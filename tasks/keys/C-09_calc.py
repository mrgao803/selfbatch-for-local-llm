#!/usr/bin/env python3
"""C-09 底稿答案：封闭生态区「穹庐-7」十二周期种群递推。

按材料给出的四式逐周期推进，每步用上一步取整后的结果继续计算。
"""
import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "C-09"
CHAIN_LENGTH = 12

K = Decimal("1000.000")
P0 = Decimal("150.000")
S0 = Decimal("0.000")

R = [
    "0.35", "0.40", "0.32", "0.45", "0.38", "0.30",
    "0.42", "0.36", "0.50", "0.33", "0.44", "0.39",
]


def q(value, digits):
    return value.quantize(Decimal("1." + "0" * digits), rounding=ROUND_HALF_UP)


def main():
    p_prev = P0
    s_prev = S0
    steps = []
    for i, r_str in enumerate(R, start=1):
        r = Decimal(r_str)
        f = q(Decimal(1) - p_prev / K, 4)
        delta = q(r * p_prev * f, 3)
        p_cur = q(p_prev + delta, 3)
        s_cur = q(s_prev + delta, 3)
        steps.append({
            "step": i,
            "outputs": {
                "F_i": float(f),
                "delta_i": float(delta),
                "P_i": float(p_cur),
                "S_i": float(s_cur),
            },
            "uses_previous": [] if i == 1 else ["P_%d" % (i - 1), "S_%d" % (i - 1)],
        })
        p_prev = p_cur
        s_prev = s_cur

    result = {
        "task_id": TASK_ID,
        "chain_length": CHAIN_LENGTH,
        "steps": steps,
        "final": {"P_12": steps[-1]["outputs"]["P_i"], "S_12": steps[-1]["outputs"]["S_i"]},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
