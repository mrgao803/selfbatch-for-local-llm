#!/usr/bin/env python3
"""C-10 底稿答案计算脚本：十二节点干线管网的流量与压力递推。

公式与参数全部取自 tasks/C-10.md 的原始材料：
    Q_i = Q_{i-1} * k_i                    节点流量（由上游输出流量与分流系数得出）
    dP_i = r_i * 1e-6 * Q_i**2             节点压降（用舍入后的 Q_i 参与计算）
    P_i = P_{i-1} - dP_i                   节点压力（由上游输出压力与本节点压降得出）

取整规则（四舍五入，ROUND_HALF_UP）：Q 保留 2 位、P 保留 3 位；
Q_i 取整后的值直接作为下一节点的输入，dP_i 不单独舍入。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "C-10"
CHAIN_LENGTH = 12

Q1 = Decimal("520.00")
P1 = Decimal("1.200")

# 节点 Z2..Z12 的（分流系数 k，压降系数 r），r 的单位为 1e-6 MPa/(m3/h)^2
NODE_DATA = [
    ("0.94", "0.30"),
    ("0.91", "0.35"),
    ("0.88", "0.40"),
    ("0.85", "0.45"),
    ("0.90", "0.30"),
    ("0.87", "0.38"),
    ("0.93", "0.28"),
    ("0.89", "0.42"),
    ("0.92", "0.33"),
    ("0.86", "0.48"),
    ("0.95", "0.26"),
]


def rnd(value, places):
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def main():
    steps = []
    steps.append({
        "step": 1,
        "outputs": {"Q1": float(rnd(Q1, 2)), "P1": float(rnd(P1, 3))},
        "uses_previous": [],
    })

    prev_q = rnd(Q1, 2)
    prev_p = rnd(P1, 3)
    for idx, (k_str, r_str) in enumerate(NODE_DATA, start=2):
        k = Decimal(k_str)
        r = Decimal(r_str)

        q = rnd(prev_q * k, 2)
        dp = r * Decimal("1e-6") * q * q
        p = rnd(prev_p - dp, 3)

        outputs = {
            "Q{}".format(idx): float(q),
            "P{}".format(idx): float(p),
        }
        steps.append({
            "step": idx,
            "outputs": outputs,
            "uses_previous": ["Q{}".format(idx - 1), "P{}".format(idx - 1)],
        })
        prev_q = q
        prev_p = p

    result = {
        "task_id": TASK_ID,
        "chain_length": CHAIN_LENGTH,
        "steps": steps,
        "final": {"Q12": float(prev_q), "P12": float(prev_p)},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
