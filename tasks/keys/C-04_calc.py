"""C-04 底稿答案：黛宁 D9 九次采样血药浓度递推（链长 9）。

按 C-04 材料里的公式与系数表逐段计算，全部数字由本脚本算出。
舍入一律用十进制「四舍五入」（ROUND_HALF_UP），每一步都使用上一步已舍入的结果。
运行：/home/sparker/miniconda3/envs/llm/bin/python tasks/keys/C-04_calc.py
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "C-04"
CHAIN_LENGTH = 9

# 材料「五、系数表」，n = 1..9
R = [Decimal(x) for x in "0.64 0.58 0.52 0.47 0.43 0.40 0.38 0.35 0.33".split()]
S = [Decimal(x) for x in "0.82 0.79 0.76 0.74 0.72 0.70 0.68 0.66 0.64".split()]
A = [Decimal(x) for x in "0.0016 0.0020 0.0022 0.0022 0.0020 0.0018 0.0015 0.0012 0.0010".split()]

DT = Decimal("2.0")  # 采样间隔（h）
Q3 = Decimal("0.001")
Q4 = Decimal("0.0001")

# 材料「三、初始条件」：第 0 小时
G_prev, C_prev, S_prev = Decimal("400.00"), Decimal("0.0000"), Decimal("0.0000")

steps = []
for n in range(1, CHAIN_LENGTH + 1):
    i = n - 1
    g = (G_prev * R[i]).quantize(Q3, rounding=ROUND_HALF_UP)
    c = (C_prev * S[i] + G_prev * A[i]).quantize(Q4, rounding=ROUND_HALF_UP)
    s = (S_prev + (C_prev + c) / Decimal("2") * DT).quantize(Q4, rounding=ROUND_HALF_UP)
    steps.append({
        "step": n,
        "outputs": {"G%d" % n: float(g), "C%d" % n: float(c), "S%d" % n: float(s)},
        "uses_previous": [] if n == 1 else ["G%d" % (n - 1), "C%d" % (n - 1), "S%d" % (n - 1)],
    })
    G_prev, C_prev, S_prev = g, c, s

# 自检：第 1 步以外，uses_previous 必须非空
for st in steps:
    if st["step"] != 1 and not st["uses_previous"]:
        raise SystemExit("step %d does not depend on previous step" % st["step"])

last = steps[-1]["outputs"]
print(json.dumps({
    "task_id": TASK_ID,
    "chain_length": CHAIN_LENGTH,
    "steps": steps,
    "final": {"G9": last["G9"], "C9": last["C9"], "S9": last["S9"]},
}, ensure_ascii=False, indent=2))
