#!/usr/bin/env python
"""阶段二运行器入口。

示例：
  # 真实联调：1 题 1 seed 1 变体 1 轮，前端能看到真数据流动
  python run_phase2.py --tasks A-01 --seeds 101 --variants V1 --rounds 1

  # 不调模型，只验证管线
  python run_phase2.py --tasks A-01 --seeds 101 --rounds 2 --variants V1 --mock

  # 正式全量
  python run_phase2.py

  # 只做匿名化
  python run_phase2.py --anonymize-only
"""
import argparse
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# mock 试跑一律写到 results/_mock，避免污染真实实验数据。
# 必须在导入 harness 之前决定（config 在导入时读该环境变量）。
_argv = sys.argv[1:]
if "--results-root" in _argv:
    os.environ["EXPERIMENT_RESULTS_DIR"] = _argv[_argv.index("--results-root") + 1]
elif "--mock" in _argv:
    os.environ["EXPERIMENT_RESULTS_DIR"] = str(_HERE / "results" / "_mock")

from harness import anonymize, runner, taskloader           # noqa: E402
from harness.config import RunConfig, ServeConfig           # noqa: E402
from harness.live import LiveSink                           # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="*", default=None, help="题号，默认全部 30 道")
    ap.add_argument("--seeds", nargs="*", type=int, default=[101, 202, 303])
    ap.add_argument("--variants", nargs="*", default=["V1", "V2", "V3"])
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--endpoint", default="completions", choices=["completions", "chat"])
    ap.add_argument("--base-url", default="http://127.0.0.1:8003")
    ap.add_argument("--outline-source", default="task_file", choices=["task_file", "model"])
    ap.add_argument("--mock", action="store_true", help="不调模型，用假数据跑通管线")
    ap.add_argument("--no-live", action="store_true", help="不写前端用的 live/state.json")
    ap.add_argument("--anonymize-only", action="store_true", help="只做匿名化，不跑生成")
    args = ap.parse_args()

    cfg = RunConfig(seeds=args.seeds, variants=args.variants, rounds=args.rounds,
                    tasks=args.tasks, outline_source=args.outline_source,
                    emit_live=not args.no_live, mock=args.mock)
    ids = args.tasks or taskloader.all_ids()
    tasks = [taskloader.load(t) for t in ids]

    if not args.anonymize_only:
        sink = LiveSink(enabled=cfg.emit_live)
        r = runner.Runner(cfg, ServeConfig(base_url=args.base_url, endpoint=args.endpoint),
                          sink)
        print(f"[run] {len(tasks)} 题 × {len(cfg.seeds)} seed × {len(cfg.variants)} 变体 "
              f"× {cfg.rounds} 轮  endpoint={args.endpoint} mock={cfg.mock}", flush=True)
        failures = []
        for t in tasks:
            try:
                r.run_task(t)
            except Exception as e:
                # 逐题隔离：一题失败不牵连其余。如实记录，不重试、不改提示词。
                failures.append((t.task_id, repr(e)[:300]))
                print(f"[FAIL] {t.task_id}: {e!r}", flush=True)
        if failures:
            print(f"[run] {len(failures)} 题失败（如实记录，未重试未修改提示词）：", flush=True)
            for tid, err in failures:
                print(f"  {tid}: {err}", flush=True)
        print("[run] 生成阶段结束", flush=True)

    mapping = anonymize.build_pairs(tasks, cfg.seeds, cfg.variants, cfg.rounds)
    print(f"[anon] 生成 {len(mapping)} 个 pair -> {anonymize.PAIRS}，"
          f"映射 -> {anonymize.MAPPING}")


if __name__ == "__main__":
    main()
