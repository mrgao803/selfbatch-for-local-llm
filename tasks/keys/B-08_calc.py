#!/usr/bin/env python
"""底稿答案：B-08 五段放电状态递推。

按 tasks/B-08.md 原始材料中的固定常数、六条递推规则与取整规则逐段计算，
结果以 JSON 打印到 stdout。全部取整采用四舍五入（半值向上进位）。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "B-08"
CHAIN_LENGTH = 5

OCV = Decimal("3.600")      # 理想开路电压 (V)
R0 = Decimal("0.0800")      # 初始内阻 (ohm)
S0 = Decimal("12.000")      # 初始剩余电量 (Ah)
I1 = Decimal("4.000")       # 第一段放电电流 (A)
A = Decimal("0.850")        # 电流衰减系数
B = Decimal("1.100")        # 内阻增长系数
C = Decimal("0.0040")       # 内阻固定增量 (ohm)
D = Decimal("0.600")        # 时长基准系数 (h)
SB = Decimal("12.000")      # 基准电量 (Ah)

PRECISION = {"I": 3, "R": 4, "t": 3, "U": 4, "Q": 3, "S": 3}


def rnd(value, digits):
    return Decimal(value).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def main():
    steps = []
    prev_i = I1
    prev_r = R0
    prev_s = S0

    for k in range(1, CHAIN_LENGTH + 1):
        if k == 1:
            i_k = rnd(I1, PRECISION["I"])
            uses_previous = []
        else:
            i_k = rnd(prev_i * A, PRECISION["I"])
            uses_previous = ["I%d" % (k - 1), "R%d" % (k - 1), "S%d" % (k - 1)]

        r_k = rnd(prev_r * B + C, PRECISION["R"])
        t_k = rnd(D * (prev_s / SB), PRECISION["t"])
        u_k = rnd(OCV - i_k * r_k, PRECISION["U"])
        q_k = rnd(i_k * t_k, PRECISION["Q"])
        s_k = rnd(prev_s - q_k, PRECISION["S"])

        steps.append({
            "step": k,
            "outputs": {
                "I%d" % k: float(i_k),
                "R%d" % k: float(r_k),
                "t%d" % k: float(t_k),
                "U%d" % k: float(u_k),
                "Q%d" % k: float(q_k),
                "S%d" % k: float(s_k),
            },
            "uses_previous": uses_previous,
        })

        prev_i, prev_r, prev_s = i_k, r_k, s_k

    result = {
        "task_id": TASK_ID,
        "chain_length": CHAIN_LENGTH,
        "steps": steps,
        "final": {"S5": steps[-1]["outputs"]["S5"]},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
