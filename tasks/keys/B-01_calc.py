"""B-01 底稿答案计算脚本：岚谷 L7 项目三季度现金流推算（链长 3）。

按 tasks/B-01.md 材料中的公式与参数逐步计算，结果以 JSON 打印到 stdout。
所有金额四舍五入保留两位小数，后续步骤使用上一步已舍入的结果。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TAU = Decimal("0.07")

C0 = Decimal("2450000.00")
RB = Decimal("1360000.00")
EB = Decimal("890000.00")


def r2(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def f(x):
    return float(r2(x))


# 第 1 步（第一季度）：仅使用材料中的期初常数
R1 = r2(RB * Decimal("0.92"))
E1 = r2(EB * Decimal("0.88"))
T1 = r2((R1 - E1) * TAU)
N1 = r2(R1 - E1 - T1)
C1 = r2(C0 + N1)

# 第 2 步（第二季度）：收入/成本由第 1 步结果乘系数得到，余额在第 1 步季末余额上累加
R2 = r2(R1 * Decimal("1.12"))
E2 = r2(E1 * Decimal("1.07"))
T2 = r2((R2 - E2) * TAU)
N2 = r2(R2 - E2 - T2)
C2 = r2(C1 + N2)

# 第 3 步（第三季度）：收入/成本由第 2 步结果乘系数得到，余额在第 2 步季末余额上累加
R3 = r2(R2 * Decimal("0.96"))
E3 = r2(E2 * Decimal("1.02"))
T3 = r2((R3 - E3) * TAU)
N3 = r2(R3 - E3 - T3)
C3 = r2(C2 + N3)

result = {
    "task_id": "B-01",
    "chain_length": 3,
    "steps": [
        {
            "step": 1,
            "outputs": {
                "R1": f(R1),
                "E1": f(E1),
                "T1": f(T1),
                "N1": f(N1),
                "C1": f(C1),
            },
            "uses_previous": [],
        },
        {
            "step": 2,
            "outputs": {
                "R2": f(R2),
                "E2": f(E2),
                "T2": f(T2),
                "N2": f(N2),
                "C2": f(C2),
            },
            "uses_previous": ["R1", "E1", "C1"],
        },
        {
            "step": 3,
            "outputs": {
                "R3": f(R3),
                "E3": f(E3),
                "T3": f(T3),
                "N3": f(N3),
                "C3": f(C3),
            },
            "uses_previous": ["R2", "E2", "C2"],
        },
    ],
    "final": {"C3": f(C3)},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
