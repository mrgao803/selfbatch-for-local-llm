#!/usr/bin/env python
"""阶段一：batch 耗时曲线（vLLM @ 127.0.0.1:8003）

按 03-executor-rules.md §3 与 04-prompt-spec.md §7：
  固定输入 ~2048 token、强制输出 256 token（ignore_eos）、
  每个 batch 预热 3 次 + 测量 5 次、取中位数、分别记录 prefill 与 decode。
batch ∈ {1,2,4,8,16}；batch=10 的单步耗时比由 8 与 16 在 log2 尺度插值（操作员裁定 D2）。
"""
import json, time, threading, urllib.request, statistics, datetime, os, sys, math

BASE = "http://127.0.0.1:8003"
MODEL = "qwen38-27b"
MODEL_PATH = "/home/sparker/test_home/test_qwen/model/qwen38_27b"
GEN = "请从 1 开始连续数数，每个数字单独一行，一直数下去，不要停止。"

# 默认集合照 03-executor-rules.md §3.2；扩展 batch 用 --batches 覆盖（属"补充"，不改动已定条目）
import argparse as _argparse
_ap = _argparse.ArgumentParser()
_ap.add_argument("--batches", nargs="*", type=int, default=[1, 2, 4, 8, 16])
_ap.add_argument("--out", default="/home/sparker/test_home/test_multi_docoder/results/phase1_batch_timing.json")
_args = _ap.parse_args()
BATCHES = _args.batches
OUT = _args.out
WARMUP, MEASURE, CTX, MAXTOK = 3, 5, 2048, 256

FILLER = ("工程记录：本段文字仅用于把输入长度填充到指定范围，与任何实验任务材料无关。"
          "现场记录表明，设备在连续运行期间各项读数保持平稳，巡检人员按班次记录数值并归档。"
          "为便于复核，所有记录均按时间顺序编号，单位与精度在表头统一注明，异常值单独标注。")

import transformers
tok = transformers.AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)


def tpl_tokens(text):
    # transformers 5.x 中 apply_chat_template(tokenize=True) 返回 BatchEncoding(dict)，
    # len() 是键数不是 token 数；必须先取字符串再单独 tokenize。
    s = tok.apply_chat_template([{"role": "user", "content": text}],
                                tokenize=False, add_generation_prompt=True)
    return len(tok(s)["input_ids"])


base_ids = tok(FILLER)["input_ids"]
pool = (base_ids * (CTX // len(base_ids) + 4))[:CTX + 200]
best = None
for F in range(max(1, CTX - 200), CTX + 1):
    txt = tok.decode(pool[:F]) + "\n\n" + GEN
    n = tpl_tokens(txt)
    if best is None or abs(n - CTX) < abs(best[1] - CTX):
        best = (F, n, txt)
FILLER_TOKENS, FULL_LEN, FULL_TEXT = best
print(f"[setup] 填充 {FILLER_TOKENS} token，模板后总长 {FULL_LEN} token（目标 {CTX}±50）", flush=True)
if abs(FULL_LEN - CTX) > 50:
    sys.exit(f"[abort] 模板后总长 {FULL_LEN}，超出 {CTX}±50，不启动测量")


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=900)


def one_request():
    pl = {"model": MODEL, "messages": [{"role": "user", "content": FULL_TEXT}],
          "max_tokens": MAXTOK, "temperature": 0.0, "ignore_eos": True, "stream": True,
          "chat_template_kwargs": {"enable_thinking": False}}
    t0 = time.perf_counter(); ttft = None; n = 0; fin = None
    for raw in post("/v1/chat/completions", pl):
        s = raw.decode().strip()
        if not s.startswith("data:"):
            continue
        b = s[5:].strip()
        if b == "[DONE]":
            break
        ch = json.loads(b)["choices"][0]
        d = ch.get("delta", {})
        if d.get("content") or d.get("reasoning"):
            if ttft is None:
                ttft = time.perf_counter()
            n += 1
        if ch.get("finish_reason"):
            fin = ch["finish_reason"]
    t1 = time.perf_counter()
    if ttft is None:
        raise RuntimeError("没有收到任何 token")
    return {"prefill_ms": (ttft - t0) * 1000, "decode_ms": (t1 - ttft) * 1000,
            "output_tokens": n, "finish": fin}


def round_of(batch):
    res, errs = [None] * batch, []

    def w(i):
        try:
            res[i] = one_request()
        except Exception as e:
            errs.append(repr(e)[:200])
    th = [threading.Thread(target=w, args=(i,)) for i in range(batch)]
    t0 = time.perf_counter()
    for t in th: t.start()
    for t in th: t.join()
    return res, errs, (time.perf_counter() - t0) * 1000


def med(xs): return statistics.median(xs) if xs else None


def p90(xs):
    return sorted(xs)[min(len(xs) - 1, int(round(0.9 * (len(xs) - 1))))] if xs else None


results = {"model": f"{MODEL}（bf16, vLLM）", "gpu": "NVIDIA GB10（统一内存，总 119 GiB）",
           "context_tokens": CTX, "output_tokens": MAXTOK,
           "sampling": "greedy(temperature=0), ignore_eos=true, enable_thinking=false",
           "measured_at": datetime.datetime.now().isoformat(),
           "filler_tokens": FILLER_TOKENS, "templated_prompt_tokens": FULL_LEN,
           "measurements": []}

for B in BATCHES:
    print(f"\n=== batch={B} 预热 {WARMUP} 轮 ===", flush=True)
    for i in range(WARMUP):
        _, errs, wall = round_of(B)
        print(f"  预热{i+1}: wall={wall/1000:.1f}s errs={len(errs)}", flush=True)
    dec, pre, tok_n, walls = [], [], [], []
    print(f"=== batch={B} 测量 {MEASURE} 轮 ===", flush=True)
    for i in range(MEASURE):
        res, errs, wall = round_of(B)
        ok = [r for r in res if r]
        if errs:
            print(f"  轮{i+1} 错误: {errs}", flush=True)
        dec.append(max(r["decode_ms"] for r in ok))
        pre.append(med([r["prefill_ms"] for r in ok]))
        tok_n.append(min(r["output_tokens"] for r in ok))
        walls.append(wall)
        print(f"  轮{i+1}: 最慢 decode={dec[-1]/1000:.2f}s prefill中位={pre[-1]:.0f}ms "
              f"tokens={tok_n[-1]} wall={wall/1000:.1f}s", flush=True)
    m = {"batch": B, "prefill_ms_median": round(med(pre), 1),
         "decode_ms_median": round(med(dec), 1), "decode_ms_p90": round(p90(dec), 1),
         "tokens_per_sec": round(256 / (med(dec) / 1000), 2) if med(dec) else None,
         "raw_decode_ms": [round(x, 1) for x in dec],
         "raw_prefill_ms": [round(x, 1) for x in pre],
         "output_tokens_per_request": tok_n[0], "wall_ms": [round(x, 1) for x in walls]}
    results["measurements"].append(m)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(results, open(OUT, "w"), ensure_ascii=False, indent=2)

d = {m["batch"]: m["decode_ms_median"] for m in results["measurements"]}
if 1 in d and 8 in d and 16 in d:
    f = (math.log2(10) - math.log2(8)) / (math.log2(16) - math.log2(8))
    dec10 = d[8] + f * (d[16] - d[8])
    results["ratio_batch10_over_batch1"] = {
        "interpolated_decode_ms_batch10": round(dec10, 1),
        "interpolation": "log2 尺度，由 batch=8 与 batch=16 插值（batch=10 未直测，D2）",
        "ratio": round(dec10 / d[1], 4),
        "ratio_batch8": round(d[8] / d[1], 4),
        "ratio_batch16": round(d[16] / d[1], 4),
        "decode_ms_batch1": d[1]}
    print(f"\n### 单步耗时比（batch=10 / batch=1）= {results['ratio_batch10_over_batch1']['ratio']}")
json.dump(results, open(OUT, "w"), ensure_ascii=False, indent=2)
print(f"\n[done] -> {OUT}", flush=True)
