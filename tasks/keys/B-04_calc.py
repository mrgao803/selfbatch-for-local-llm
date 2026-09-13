#!/usr/bin/env python
"""B-04 底稿答案：松汀 W-7 仓 橡砂 R2 四周期库存周转推算。

严格按 tasks/B-04.md 材料里的公式与参数逐周期计算：
    E_i = 四舍五入取整(S_{i-1} * r_i)
    S_i = S_{i-1} + I_i - E_i
    T_i = E_i / ((S_{i-1} + S_i) / 2)   （保留两位小数）
"""
import json
from decimal import Decimal, ROUND_HALF_UP

TWO = Decimal("0.01")


def half_up_int(x: Decimal) -> int:
    return int(x.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def two_places(x: Decimal) -> float:
    return float(x.quantize(TWO, rounding=ROUND_HALF_UP))


S0 = Decimal("1500")
I = {1: Decimal("380"), 2: Decimal("300"), 3: Decimal("260"), 4: Decimal("240")}
r = {1: Decimal("0.32"), 2: Decimal("0.28"), 3: Decimal("0.35"), 4: Decimal("0.22")}

prev = S0
steps = []
e_total = 0
for i in range(1, 5):
    E = half_up_int(prev * r[i])
    S = prev + I[i] - E
    T = two_places(E / ((prev + S) / Decimal("2")))
    steps.append({
        "step": i,
        "outputs": {"E%d" % i: E, "S%d" % i: int(S), "T%d" % i: T},
        "uses_previous": [] if i == 1 else ["S%d" % (i - 1)],
    })
    e_total += E
    prev = S

result = {
    "task_id": "B-04",
    "chain_length": 4,
    "steps": steps,
    "final": {"S4": int(prev), "Etot": e_total},
}
print(json.dumps(result, ensure_ascii=False, indent=2))
