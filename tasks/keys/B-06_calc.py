#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B-06 底稿答案：KX-7 温升—功率耦合推算（4 步）。

按材料给出的公式与参数逐步计算；每一步先把结果按材料规定的精度取整，
再把取整后的值用于后续步骤。数字全部由本脚本算出，无手算。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

W = Decimal("0.01")    # 功率、温度：2 位小数
F = Decimal("0.0001")  # 修正因子、效率：4 位小数


def q(value, exp):
    """按材料规定精度四舍五入（ROUND_HALF_UP），返回 Decimal。"""
    return Decimal(value).quantize(exp, rounding=ROUND_HALF_UP)


# ---- 初始条件（材料常数）----
P0 = Decimal("620.00")  # 基准功率 W
T0 = Decimal("22.00")   # 基准环境温度 ℃

steps = []

# ---- 第 1 步：负载修正 ----
L1 = Decimal("0.88")
P1 = q(P0 * L1, W)
steps.append({
    "step": 1,
    "outputs": {"L1": float(L1), "P1": float(P1)},
    "uses_previous": [],
})

# ---- 第 2 步：温升计算 ----
K2 = Decimal("0.035")
dT2 = q(P1 * K2, W)
T2 = q(T0 + dT2, W)
steps.append({
    "step": 2,
    "outputs": {"K2": float(K2), "dT2": float(dT2), "T2": float(T2)},
    "uses_previous": ["P1"],
})

# ---- 第 3 步：温度修正 ----
F3 = q(Decimal(1) - (T2 - T0) * Decimal("0.0028"), F)
P3 = q(P1 * F3, W)
steps.append({
    "step": 3,
    "outputs": {"F3": float(F3), "P3": float(P3)},
    "uses_previous": ["P1", "T2"],
})

# ---- 第 4 步：效率修正与温度更新 ----
eta4 = q(Decimal("0.90") + (T2 - T0) * Decimal("0.0007"), F)
P4 = q(P3 * eta4, W)
T4 = q(T2 + P4 * Decimal("0.010"), W)
steps.append({
    "step": 4,
    "outputs": {"eta4": float(eta4), "P4": float(P4), "T4": float(T4)},
    "uses_previous": ["P3", "T2"],
})

# ---- 串行自检：第 1 步之后每步都必须用到前面的输出 ----
for s in steps[1:]:
    assert s["uses_previous"], "第 %d 步未依赖前一步，不是串行题" % s["step"]

result = {
    "task_id": "B-06",
    "chain_length": 4,
    "steps": steps,
    "final": {"P4": float(P4), "T4": float(T4)},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
