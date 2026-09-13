"""实时状态输出，供前端展示「N 段同时在写 / 汇总后再写」。

落盘 results/live/state.json（原子写），前端轮询即可。写盘做节流，避免每 token 一次 IO。
"""
import json
import os
import threading
import time
from pathlib import Path

from .config import RESULTS_DIR

LIVE_DIR = RESULTS_DIR / "live"
THROTTLE = 0.30


class LiveSink:
    def __init__(self, enabled: bool = True, live_dir: Path = LIVE_DIR):
        self.enabled = enabled
        self.dir = live_dir
        self.state_path = live_dir / "state.json"
        self.events_path = live_dir / "events.jsonl"
        self._lock = threading.Lock()
        self._last = 0.0
        self.state = {}

    # ---- 生命周期 ----
    def begin_task(self, task, seed):
        with self._lock:
            self.state = {"task_id": task.task_id, "cls": task.cls, "n": task.n,
                          "chain": task.chain, "seed": seed, "condition": None,
                          "variant": None, "round": None, "phase": "准备",
                          "segments": [], "updated_at": time.time()}
        self._flush(force=True)
        self._event("task_start", {"task_id": task.task_id, "seed": seed})

    def begin_phase(self, condition, variant, round_, titles, n):
        if condition == "A0":
            label = "一次写完（基线）"
        elif condition == "A1":
            label = "N 段并行生成"
        elif condition.startswith("A2"):
            label = f"第 {round_} 轮 · {variant} 汇总融合"
        else:
            label = condition
        with self._lock:
            self.state.update({
                "condition": condition, "variant": variant, "round": round_,
                "phase": label,
                "segments": [{"i": i + 1, "title": titles[i], "text": "", "reasoning": "",
                              "tokens": 0, "state": "writing"} for i in range(n)],
                "updated_at": time.time()})
        self._flush(force=True)
        self._event("phase_start", {"condition": condition, "variant": variant, "round": round_})

    def delta(self, i, piece, kind):
        with self._lock:
            seg = self.state["segments"][i - 1]
            if kind == "reasoning":
                seg["reasoning"] += piece
            else:
                seg["text"] += piece
            seg["tokens"] += 1
        self._flush()

    def segment_done(self, i, state="done"):
        with self._lock:
            self.state["segments"][i - 1]["state"] = state
        self._flush(force=True)

    def end_phase(self):
        self._event("phase_end", {"condition": self.state.get("condition")})

    # ---- 落盘 ----
    def _flush(self, force: bool = False):
        if not self.enabled:
            return
        now = time.time()
        if not force and now - self._last < THROTTLE:
            return
        # 整段写入必须在锁内：N 个线程会同时 force flush，否则 os.replace 会撞车
        with self._lock:
            if not force and time.time() - self._last < THROTTLE:
                return
            self._last = time.time()
            self.state["updated_at"] = self._last
            payload = json.dumps(self.state, ensure_ascii=False)
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = self.dir / f"state.{os.getpid()}.{threading.get_ident()}.tmp"
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, self.state_path)

    def _event(self, kind, data):
        if not self.enabled:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "type": kind, **data},
                               ensure_ascii=False) + "\n")
