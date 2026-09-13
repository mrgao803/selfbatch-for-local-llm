#!/bin/bash
# 等阶段一跑完 → 自动做真实联调（真模型、真任务），前端能看到真数据流动。
# 用 setsid nohup 启动，脱离 SSH 会话。
cd /home/sparker/test_home/test_multi_docoder || exit 1
PY=/home/sparker/miniconda3/envs/llm/bin/python
PHASE1_PID="${1:-2681421}"

echo "[watch] 等待阶段一 (pid $PHASE1_PID) 结束 … $(date +%H:%M:%S)"
while kill -0 "$PHASE1_PID" 2>/dev/null; do sleep 20; done
echo "[watch] 阶段一已结束 $(date +%H:%M:%S)"
echo "---- 阶段一结果 ----"
"$PY" -m json.tool results/phase1_batch_timing.json 2>/dev/null | tail -30
echo "---- 单步耗时比 ----"
"$PY" -c "import json;d=json.load(open('results/phase1_batch_timing.json'));r=d.get('ratio_batch10_over_batch1');print(r if r else '（未算出）')"
echo
echo "[watch] 探针：/v1/completions + 思考占比 $(date +%H:%M:%S)"
"$PY" - <<'PROBE'
import json, time, urllib.request
BASE="http://127.0.0.1:8003"
def post(path, pl):
    r=urllib.request.Request(BASE+path, data=json.dumps(pl).encode(),
                             headers={"Content-Type":"application/json"})
    return urllib.request.urlopen(r, timeout=300)
P="请从 1 开始连续数数，每个数字单独一行，一直数下去，不要停止。"
# 1) 原生 completions 是否可用、ignore_eos 是否生效
try:
    r=json.load(post("/v1/completions", {"model":"qwen38-27b","prompt":P,
        "max_tokens":32,"temperature":0,"ignore_eos":True}))
    u=r.get("usage",{}); t=r["choices"][0]["text"]
    print("  原生 completions: 可用  completion_tokens=%s  finish=%s"
          %(u.get("completion_tokens"), r["choices"][0].get("finish_reason")))
    print("  输出前80字:", repr(t[:80]))
except Exception as e:
    print("  原生 completions: 不可用", repr(e)[:160])
# 2) 一次 A2 规模的请求，看思考占多少
try:
    r=json.load(post("/v1/completions", {"model":"qwen38-27b",
        "prompt":"请写一段200字左右的产品说明，主题：家用智能音箱。","max_tokens":600,"temperature":0.7,"top_p":0.9,"seed":101}))
    u=r.get("usage",{}); t=r["choices"][0]["text"]
    print("  A2 规模请求: completion_tokens=%s  finish=%s  正文长度=%d"
          %(u.get("completion_tokens"), r["choices"][0].get("finish_reason"), len(t)))
    print("  正文前80字:", repr(t[:80]))
except Exception as e:
    print("  A2 规模请求失败", repr(e)[:160])
PROBE
echo
echo "[watch] 开始真实联调：A-01 × 1 seed × V1 × 1 轮 $(date +%H:%M:%S)"
"$PY" -u run_phase2.py --tasks A-01 --seeds 101 --variants V1 --rounds 1
echo "[watch] 联调结束 $(date +%H:%M:%S)"
