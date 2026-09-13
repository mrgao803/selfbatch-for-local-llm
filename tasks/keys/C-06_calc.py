"""C-06 底稿答案：项目「青松」十期滚动财务推算。

规则与材料一致：
  R_i = 0.70 * C_{i-1} + G_i
  E_i = 0.55 * R_i + 45.00
  T_i = 0.25 * (R_i - E_i)，税前利润 <= 0 时取 0.00
  P_i = R_i - E_i - T_i
  C_i = C_{i-1} + P_i - 2.00
每步四舍五入保留两位小数后，再作为下一步输入。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

D = Decimal


def r2(x):
    return x.quantize(D("0.01"), rounding=ROUND_HALF_UP)


C0 = D("660.00")
ORDER_BASE = ["51", "47", "43", "39", "35", "31", "27", "23", "19", "15"]
RATE_REVENUE = D("0.70")
RATE_VARIABLE_COST = D("0.55")
FIXED_COST = D("45.00")
RATE_TAX = D("0.25")
FIXED_FEE = D("2.00")


def main():
    cash = C0
    steps = []
    for i, g in enumerate(ORDER_BASE, start=1):
        revenue = r2(RATE_REVENUE * cash + D(g))
        cost = r2(RATE_VARIABLE_COST * revenue + FIXED_COST)
        pretax = revenue - cost
        tax = r2(RATE_TAX * pretax) if pretax > 0 else D("0.00")
        profit = r2(revenue - cost - tax)
        cash = r2(cash + profit - FIXED_FEE)
        steps.append(
            {
                "step": i,
                "outputs": {
                    f"R{i}": float(revenue),
                    f"E{i}": float(cost),
                    f"T{i}": float(tax),
                    f"P{i}": float(profit),
                    f"C{i}": float(cash),
                },
                "uses_previous": [] if i == 1 else [f"C{i - 1}"],
            }
        )

    result = {
        "task_id": "C-06",
        "chain_length": 10,
        "steps": steps,
        "final": {"C10": float(cash)},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
