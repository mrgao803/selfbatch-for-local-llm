#!/usr/bin/env python3
"""B-03 底稿答案计算脚本：云枢 P7 三级递进促销的折价与毛利递推。

公式与参数全部取自 tasks/B-03.md 的原始材料：
    P_i = P_{i-1} * d_i                     逐级折后价（P0 为挂牌价）
    C_i = C_{i-1} + (P_{i-1} - C_{i-1}) * s_i   逐级成本（C0 为基础成本）
    M_i = P_i - C_i                         该级毛利
    L_i = P_{i-1} - P_i                     该级让利额
    g_i = M_i / P_i                         该级毛利率（百分数）
    T3  = L1 + L2 + L3                      三级累计让利额

取整规则（四舍五入，ROUND_HALF_UP）：折后价、成本、毛利、让利额、累计让利额
均保留 2 位小数（单位：元）；毛利率保留 2 位小数（单位：%）。每一步取整后的
折后价与成本直接作为下一级的输入。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "B-03"
CHAIN_LENGTH = 3

P0 = Decimal("1280.00")
C0 = Decimal("760.00")

DISCOUNT = {1: Decimal("0.92"), 2: Decimal("0.88"), 3: Decimal("0.90")}
COST_ADD = {1: Decimal("0.20"), 2: Decimal("0.10"), 3: Decimal("0.08")}

MONEY = 2
PCT = 2
HUNDRED = Decimal(100)


def rnd(value, places):
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def main():
    steps = []
    prev_p, prev_c = P0, C0
    l_values = []

    for i in (1, 2, 3):
        p = rnd(prev_p * DISCOUNT[i], MONEY)
        if i == 1:
            c = rnd(C0 + (P0 - C0) * COST_ADD[i], MONEY)
        else:
            c = rnd(prev_c + (prev_p - prev_c) * COST_ADD[i], MONEY)
        m = rnd(p - c, MONEY)
        l = rnd(prev_p - p, MONEY)
        g = rnd(m / p * HUNDRED, PCT)
        l_values.append(l)

        outputs = {
            "P{}".format(i): float(p),
            "C{}".format(i): float(c),
            "M{}".format(i): float(m),
            "L{}".format(i): float(l),
            "g{}".format(i): float(g),
        }

        if i == 1:
            uses_previous = []
        elif i == 2:
            uses_previous = ["P1", "C1"]
        else:
            uses_previous = ["P2", "C2", "L1", "L2"]
            t3 = rnd(l_values[0] + l_values[1] + l_values[2], MONEY)
            outputs["T3"] = float(t3)

        steps.append({
            "step": i,
            "outputs": outputs,
            "uses_previous": uses_previous,
        })
        prev_p, prev_c = p, c

    final = dict(steps[-1]["outputs"])
    result = {
        "task_id": TASK_ID,
        "chain_length": CHAIN_LENGTH,
        "steps": steps,
        "final": final,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
