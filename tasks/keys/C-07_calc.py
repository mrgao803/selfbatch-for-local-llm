#!/usr/bin/env python3
"""底稿答案计算脚本：C-07 十一级供应链库存与补货递推。

严格按 tasks/C-07.md 材料中的公式与参数逐级计算：
    Si = Ai - Ci
    Qi = ai * (Ti - Si)  若 Ti - Si > 0，否则 0.00
    A(i+1) = (Si + Qi) * (1 - pi)
所有中间量与最终结果四舍五入保留两位小数，且每步使用上一步保留两位小数后的值。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TWO = Decimal("0.01")


def r2(x):
    return Decimal(x).quantize(TWO, rounding=ROUND_HALF_UP)


A1 = Decimal("3000.00")

C = ["420.00", "380.00", "350.00", "400.00", "330.00", "360.00",
     "310.00", "340.00", "290.00", "370.00", "300.00"]
T = ["1500.00", "1350.00", "1200.00", "1100.00", "1000.00", "950.00",
     "900.00", "850.00", "800.00", "780.00", "760.00"]
ALPHA = ["0.60", "0.50", "0.70", "0.40", "0.60", "0.50",
         "0.80", "0.45", "0.60", "0.55", "0.50"]
P = ["0.05", "0.04", "0.06", "0.03", "0.05", "0.07",
     "0.04", "0.06", "0.03", "0.05", "0.05"]

N = 11


def main():
    steps = []
    arrival = A1
    q_total = Decimal("0.00")
    last = {}

    for i in range(N):
        Ai = arrival
        Si = r2(Ai - Decimal(C[i]))
        deficit = Decimal(T[i]) - Si
        Qi = r2(Decimal(ALPHA[i]) * deficit) if deficit > 0 else Decimal("0.00")
        q_total = r2(q_total + Qi)

        outputs = {"S%d" % (i + 1): float(Si), "Q%d" % (i + 1): float(Qi)}
        if i == 0:
            uses = []
        else:
            uses = ["S%d" % i, "Q%d" % i]

        if i < N - 1:
            arrival = r2((Si + Qi) * (Decimal(1) - Decimal(P[i])))
            outputs["A%d" % (i + 2)] = float(arrival)
        else:
            last = {"S11": float(Si), "Q11": float(Qi), "Q_total": float(q_total)}

        steps.append({"step": i + 1, "outputs": outputs, "uses_previous": uses})

    result = {
        "task_id": "C-07",
        "chain_length": N,
        "steps": steps,
        "final": last,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
