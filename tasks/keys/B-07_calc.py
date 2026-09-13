"""B-07 底稿答案计算脚本：作物「禾试 H-4」四阶段生物量递推（链长 4）。

按 tasks/B-07.md 材料中的公式与参数逐阶段计算，结果以 JSON 打印到 stdout。
生物量 B 与净增生物量 dB 保留两位小数，限制因子 L 与平均每日净增 v 保留四位小数，
均按四舍五入处理；后一阶段一律使用前一阶段已取整后的生物量。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

B0 = Decimal("120.00")
B_CAP = Decimal("800.00")
L_MIN = Decimal("0.1000")
L_MAX = Decimal("1.0000")

RATES = {1: Decimal("0.40"), 2: Decimal("0.55"), 3: Decimal("0.45"), 4: Decimal("0.30")}
DAYS = {1: Decimal("18"), 2: Decimal("15"), 3: Decimal("14"), 4: Decimal("12")}


def q(x, digits):
    return x.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def f(x):
    return float(x)


steps = []
prev_b = B0
prev_label = None
for i in range(1, 5):
    # 限制因子取决于本阶段开始时的生物量：第 1 阶段用材料常数 B0，其后各阶段用上一步算出的生物量
    L = q((B_CAP - prev_b) / B_CAP, 4)
    if L > L_MAX:
        L = L_MAX
    if L < L_MIN:
        L = L_MIN
    B = q(prev_b * (1 + RATES[i] * L), 2)
    dB = q(B - prev_b, 2)
    v = q(dB / DAYS[i], 4)

    steps.append(
        {
            "step": i,
            "outputs": {f"L{i}": f(L), f"B{i}": f(B), f"dB{i}": f(dB), f"v{i}": f(v)},
            "uses_previous": [] if prev_label is None else [prev_label],
        }
    )
    prev_b = B
    prev_label = f"B{i}"

delta_total = q(sum(Decimal(str(s["outputs"][f"dB{s['step']}"])) for s in steps), 2)

result = {
    "task_id": "B-07",
    "chain_length": 4,
    "steps": steps,
    "final": {"B4": steps[-1]["outputs"]["B4"], "delta_total": f(delta_total)},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
