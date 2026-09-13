#!/usr/bin/env python3
"""C-01 底稿答案计算脚本：八级串联反应器的收率与物料递推。

公式与参数全部取自 tasks/C-01.md 的原始材料：
    f_i  = 1 + a * (T_i - T_ref)          温度修正因子
    eta_i = eta_base_i * f_i              修正收率
    P_i  = P_{i-1} * eta_i                逐级产物量
    W_i  = P_{i-1} - P_i                  该级损耗量
    Y    = P_8 / P_0                      全程总收率

取整规则（四舍五入，ROUND_HALF_UP）：f 保留 4 位、eta 保留 6 位、
P 与 W 保留 3 位、Y 保留 6 位；P_i 取整后的值直接作为下一级输入。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "C-01"
CHAIN_LENGTH = 8

P0 = Decimal("1200.000")
T_REF = Decimal("65.0")
ALPHA = Decimal("0.0015")

# (基础收率, 实际温度)，顺序对应 R1..R8
STAGE_DATA = [
    ("0.930", "63.0"),
    ("0.915", "67.5"),
    ("0.902", "61.0"),
    ("0.888", "69.0"),
    ("0.905", "66.0"),
    ("0.875", "71.5"),
    ("0.893", "64.5"),
    ("0.860", "68.0"),
]


def rnd(value, places):
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def main():
    steps = []
    previous_p = P0
    for idx, (base_str, temp_str) in enumerate(STAGE_DATA, start=1):
        base = Decimal(base_str)
        temp = Decimal(temp_str)

        f = rnd(Decimal(1) + ALPHA * (temp - T_REF), 4)
        eta = rnd(base * f, 6)
        p = rnd(previous_p * eta, 3)
        w = rnd(previous_p - p, 3)

        outputs = {
            "f{}".format(idx): float(f),
            "eta{}".format(idx): float(eta),
            "P{}".format(idx): float(p),
            "W{}".format(idx): float(w),
        }
        uses_previous = [] if idx == 1 else ["P{}".format(idx - 1)]
        steps.append({
            "step": idx,
            "outputs": outputs,
            "uses_previous": uses_previous,
        })
        previous_p = p

    overall = rnd(previous_p / P0, 6)

    result = {
        "task_id": TASK_ID,
        "chain_length": CHAIN_LENGTH,
        "steps": steps,
        "final": {"P8": float(previous_p), "Y": float(overall)},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
