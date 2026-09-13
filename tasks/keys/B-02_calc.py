"""B-02 底稿答案计算脚本：露引 L7 三批次配方用量递推（链长 3）。

按 tasks/B-02.md 材料中的公式与参数逐步计算，结果以 JSON 打印到 stdout。
每批用量保留三位小数、金额保留两位小数；后续各批一律取前一批已保留到
规定精度的结果参与计算。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

Q = Decimal("500.0")        # 每批成品灌装量（L）
ETA = Decimal("0.92")       # 基粉留存折算系数
T = Decimal("4.800")        # 目标固形物含量（%）
M1 = Decimal("42.0")        # 第 1 批基粉投料量（kg）

P_BASE = Decimal("26.40")   # 基粉单价（元/kg）
P_SWEET = Decimal("58.00")  # 甜味剂单价（元/kg）
P_ACID = Decimal("12.50")   # 酸度调节剂单价（元/kg）

K_SWEET = Decimal("0.035")  # 甜味剂相对基粉的比例
D_ACID = Decimal("220")     # 酸度调节剂相对基粉的除数


def r3(x):
    return x.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def r2(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def f(x):
    return float(x)


def batch(i, m):
    """由该批基粉投料量 m 算出该批的 S、B、A、C。"""
    s = r3(m * ETA / Q * Decimal("100"))
    b = r3(m * K_SWEET)
    a = r3(m / D_ACID)
    c = r2(m * P_BASE + b * P_SWEET + a * P_ACID)
    return s, b, a, c


# 第 1 批：只使用材料给出的常数
M_1 = r3(M1)
S_1, B_1, A_1, C_1 = batch(1, M_1)

# 第 2 批：投料量由第 1 批的 M1 与 S1 递推
M_2 = r3(M_1 * (Decimal("1") + (T - S_1) / T))
S_2, B_2, A_2, C_2 = batch(2, M_2)

# 第 3 批：投料量由第 2 批的 M2 与 S2 递推
M_3 = r3(M_2 * (Decimal("1") + (T - S_2) / T))
S_3, B_3, A_3, C_3 = batch(3, M_3)

# 三批累计原料总成本：使用各批已保留两位小数的成本
C_TOTAL = r2(C_1 + C_2 + C_3)

result = {
    "task_id": "B-02",
    "chain_length": 3,
    "steps": [
        {
            "step": 1,
            "outputs": {
                "M1": f(M_1),
                "S1": f(S_1),
                "B1": f(B_1),
                "A1": f(A_1),
                "C1": f(C_1),
            },
            "uses_previous": [],
        },
        {
            "step": 2,
            "outputs": {
                "M2": f(M_2),
                "S2": f(S_2),
                "B2": f(B_2),
                "A2": f(A_2),
                "C2": f(C_2),
            },
            "uses_previous": ["M1", "S1"],
        },
        {
            "step": 3,
            "outputs": {
                "M3": f(M_3),
                "S3": f(S_3),
                "B3": f(B_3),
                "A3": f(A_3),
                "C3": f(C_3),
            },
            "uses_previous": ["M2", "S2"],
        },
    ],
    "final": {"C_total": f(C_TOTAL)},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
