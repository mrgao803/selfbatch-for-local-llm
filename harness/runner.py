"""阶段二运行器：严格按 04-prompt-spec.md §五 的执行顺序。

红线（违反即作废）：
  1. R-A1 提示词里只有 材料 + 大纲，绝不含任何其他部分的正文 —— 由 prompts.r_a1 结构保证，
     本文件额外做运行时断言。
  2. 融合轮次用新段【替换】旧段，历史不进提示词。
  3. 输出照原样记录，不重跑、不修正；只有请求报错才重试并标 retry=true。

思考处理（操作员 2026-09-13 裁定）：两个条件**都保留思考**（对称），但**思考从正文里剥掉**：
  - `{seg}.txt`      = 剥掉思考后的正文（下游一切用途只用它）
  - `{seg}.think.txt`= 思考内容（单独存档）
  - `{seg}.raw.txt`  = 模型原始输出，逐字，作为自证材料
  因此 A2 的提示词里也不含思考 → 融合轮看到的是干净的文档。
"""
import datetime
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import prompts
from .client import Client, MockClient, prompt_hash, split_thinking
from .config import RESULTS_DIR, RunConfig, ServeConfig
from .live import LiveSink


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _raw_dir(task_id):
    return RESULTS_DIR / "raw" / task_id


class Runner:
    def __init__(self, cfg: RunConfig, srv: ServeConfig | None = None, sink: LiveSink | None = None,
                 log=print):
        self.cfg = cfg
        self.srv = srv or ServeConfig()
        self.client = MockClient() if cfg.mock else Client(self.srv)
        self.sink = sink or LiveSink(enabled=cfg.emit_live)
        self.log = log

    # ---------- 单段请求（带实时回显） ----------
    def _one(self, prompt, max_tokens, seed, task_id, rtype, round_, seg, records, lock, sink_i):
        def on_delta(piece, kind):
            self.sink.delta(sink_i, piece, kind)
        r = self.client.complete(prompt, max_tokens, seed, on_delta=on_delta)
        body, think = split_thinking(r["text"])
        if r.get("reasoning"):
            think = (r["reasoning"] + ("\n" + think if think else "")).strip()
        rec = {"task_id": task_id, "request_type": rtype, "seed": seed, "round": round_,
               "segment": seg, "prefill_ms": round(r["prefill_ms"], 1),
               "decode_ms": round(r["decode_ms"], 1), "output_tokens": r["output_tokens"],
               "body_tokens_est": None, "think_chars": len(think),
               "wall_clock_ms": round(r["wall_clock_ms"], 1), "retry": r.get("retry", False),
               "truncated": r.get("finish_reason") == "length",
               "prompt_hash": prompt_hash(prompt),
               "timestamp": datetime.datetime.now().isoformat()}
        with lock:
            records.append(rec)
        d = _raw_dir(task_id) / rtype / str(round_)
        _write(d / f"{seg}.txt", body)                 # 下游只用这个
        _write(d / f"{seg}.raw.txt", r["text"])        # 自证：模型原始输出，逐字
        if think:
            _write(d / f"{seg}.think.txt", think)
        return body

    def _parallel(self, task, prompts_list, max_tokens, seed, rtype, round_, records, lock):
        n = len(prompts_list)
        out = [None] * n
        errors = []
        variant = rtype.split("-", 1)[1] if rtype.startswith("A2-") else None

        def w(idx):
            try:
                out[idx] = self._one(prompts_list[idx], max_tokens, seed, task.task_id,
                                     rtype, round_, idx + 1, records, lock, idx + 1)
            except Exception as e:      # 只有请求类错误会走到这里
                errors.append((idx + 1, repr(e)[:200]))
            finally:
                self.sink.segment_done(idx + 1)
        self.sink.begin_phase(rtype, variant, round_, task.titles, n)
        with ThreadPoolExecutor(max_workers=n) as ex:
            list(ex.map(w, range(n)))
        self.sink.end_phase()
        if errors:
            raise RuntimeError(f"{task.task_id} {rtype} round={round_} 段失败: {errors}")
        return out

    # ---------- 单题 ----------
    def run_task(self, task) -> list[dict]:
        cfg = self.cfg
        records, lock = [], threading.Lock()
        timing_path = RESULTS_DIR / "timing" / f"{task.task_id}.json"
        # A2 预算：题面声明的 600 装不下「思考 + 修订正文」（实测 9/10 段被截断在思考里），
        # 故 A2 与 A0/A1 同预算。记入 DECISIONS 作为对 04 §六 的必要偏离。
        a2_max = max(task.max_tokens_a2, task.max_tokens_a01)

        if cfg.outline_source == "model":
            p = prompts.r_out(task)
            r = self.client.complete(p, task.max_tokens_a01, cfg.seeds[0])
            outline, _th = split_thinking(r["text"])
            _write(_raw_dir(task.task_id) / "OUT" / "0" / "1.txt", outline)
            self.log(f"[{task.task_id}] R-OUT 生成大纲 {len(outline)} 字")
        else:
            outline = task.outline
        if len(task.titles) != task.n:
            raise ValueError(f"{task.task_id}: 标题数 != N")

        for seed in cfg.seeds:
            self.sink.begin_task(task, seed)
            self.log(f"\n[{task.task_id}] seed={seed} 开始")

            # --- A0 基线：一次写完 ---
            self.sink.begin_phase("A0", None, None, ["完整文档"], 1)
            p0 = prompts.r_a0(task, outline)
            a0 = self._one(p0, task.max_tokens_a01, seed, task.task_id, "A0", 0, 1,
                           records, lock, 1)
            self.sink.segment_done(1)
            self.sink.end_phase()
            self.log(f"  A0 完成 {len(a0)} 字")

            # --- A1 分段并行（各段互不可见） ---
            ps = [prompts.r_a1(task, outline, i) for i in range(1, task.n + 1)]
            for i, p in enumerate(ps, 1):
                assert task.material in p and task.titles[i - 1] in p, "A1 提示词缺材料或标题"
            base = self._parallel(task, ps, task.max_tokens_a01, seed, "A1", 0, records, lock)
            self.log(f"  A1 完成 {task.n} 段，第 1 段 {len(base[0])} 字")

            # --- A2 三个变体各自独立，都从 base 出发，跑满 rounds 轮 ---
            for variant in cfg.variants:
                cur = list(base)
                for k in range(1, cfg.rounds + 1):
                    ps = [prompts.r_a2(task, variant, task.titles, cur, i)
                          for i in range(1, task.n + 1)]
                    cur = self._parallel(task, ps, a2_max, seed,
                                         f"A2-{variant}", k, records, lock)
                self.log(f"  A2-{variant} 跑满 {cfg.rounds} 轮（max_tokens={a2_max}）")

            with lock:
                snap = list(records)
            timing_path.parent.mkdir(parents=True, exist_ok=True)
            timing_path.write_text(json.dumps(
                {"task_id": task.task_id, "a2_max_tokens": a2_max, "records": snap,
                 "summary": _summary(snap)}, ensure_ascii=False, indent=2), encoding="utf-8")
        return records


def _summary(records: list[dict]) -> dict:
    """A0 总耗时、A2 每轮总耗时（该轮最慢那段）。03 §4.6"""
    s = {"A0_wall_clock_ms": None, "A2_round_wall_clock_ms": {}}
    for r in records:
        if r["request_type"] == "A0":
            s["A0_wall_clock_ms"] = r["wall_clock_ms"]
        elif r["request_type"].startswith("A2-"):
            key = f"{r['request_type']}|seed{r['seed']}|round{r['round']}"
            s["A2_round_wall_clock_ms"][key] = max(
                s["A2_round_wall_clock_ms"].get(key, 0), r["wall_clock_ms"])
    return s
