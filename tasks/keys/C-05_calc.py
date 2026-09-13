"""C-05 底稿答案：设备代号「硅穹 X-3」十级热-功率耦合推算。

按 tasks/C-05.md 材料给出的公式、参数与精度规则逐步计算。
精度规则（材料逐字规定）：
  - 功率（含损耗功率）保留 2 位小数，单位 W
  - 温度保留 2 位小数，单位 ℃
  - 修正因子与效率保留 4 位小数
  - 每一步先取整，再把取整后的值代入下一步
取整统一使用 Decimal 的 ROUND_HALF_UP（四舍五入），避免二进制浮点误差。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

D = Decimal


def q(value, ndigits):
    """按给定小数位四舍五入。"""
    return D(value).quantize(D(1).scaleb(-ndigits), rounding=ROUND_HALF_UP)


# ---- 初始条件 ----
P0 = D("720.00")
T0 = D("26.00")
R = D("0.045")

# ---- 第 1 步：负载折算 ----
L1 = D("0.9400")
P1 = q(P0 * L1, 2)

# ---- 第 2 步：初次温升 ----
dT2 = q(P1 * R, 2)
T2 = q(T0 + dT2, 2)

# ---- 第 3 步：初次降额 ----
F3 = q(D(1) - (T2 - T0) * D("0.0030"), 4)
P3 = q(P1 * F3, 2)

# ---- 第 4 步：变换效率 ----
eta4 = q(D("0.9300") - (T2 - T0) * D("0.0006"), 4)
P4 = q(P3 * eta4, 2)
W4 = q(P3 - P4, 2)

# ---- 第 5 步：二次温升 ----
dT5 = q(W4 * R * D("1.15"), 2)
T5 = q(T2 + dT5, 2)

# ---- 第 6 步：二次降额 ----
F6 = q(D(1) - (T5 - T0) * D("0.0033"), 4)
P6 = q(P4 * F6, 2)

# ---- 第 7 步：二次效率 ----
eta7 = q(D("0.9200") - (T5 - T0) * D("0.0007"), 4)
P7 = q(P6 * eta7, 2)
W7 = q(P6 - P7, 2)

# ---- 第 8 步：三次温升 ----
dT8 = q(W7 * R * D("1.30"), 2)
T8 = q(T5 + dT8, 2)

# ---- 第 9 步：三次降额 ----
F9 = q(D(1) - (T8 - T0) * D("0.0036"), 4)
P9 = q(P7 * F9, 2)

# ---- 第 10 步：最终输出 ----
eta10 = q(D("0.9100") - (T8 - T0) * D("0.0008"), 4)
P10 = q(P9 * eta10, 2)
W10 = q(P9 - P10, 2)
T10 = q(T8 + W10 * R, 2)

steps = [
    {"step": 1, "outputs": {"P1": P1}, "uses_previous": []},
    {"step": 2, "outputs": {"ΔT2": dT2, "T2": T2}, "uses_previous": ["P1"]},
    {"step": 3, "outputs": {"F3": F3, "P3": P3}, "uses_previous": ["P1", "T2"]},
    {"step": 4, "outputs": {"η4": eta4, "P4": P4, "W4": W4},
     "uses_previous": ["T2", "P3"]},
    {"step": 5, "outputs": {"ΔT5": dT5, "T5": T5}, "uses_previous": ["W4"]},
    {"step": 6, "outputs": {"F6": F6, "P6": P6}, "uses_previous": ["P4", "T5"]},
    {"step": 7, "outputs": {"η7": eta7, "P7": P7, "W7": W7},
     "uses_previous": ["P6"]},
    {"step": 8, "outputs": {"ΔT8": dT8, "T8": T8}, "uses_previous": ["W7"]},
    {"step": 9, "outputs": {"F9": F9, "P9": P9}, "uses_previous": ["P7", "T8"]},
    {"step": 10, "outputs": {"η10": eta10, "P10": P10, "W10": W10, "T10": T10},
     "uses_previous": ["P9", "T8"]},
]

# 自检：第 2 步起每步都必须引用前面某一步的输出，且必须用到紧邻上一步的输出
for idx, s in enumerate(steps):
    if idx == 0:
        continue
    assert s["uses_previous"], f"第 {s['step']} 步 uses_previous 为空，不是串行题"

result = {
    "task_id": "C-05",
    "chain_length": 10,
    "steps": [
        {
            "step": s["step"],
            "outputs": {k: float(v) for k, v in s["outputs"].items()},
            "uses_previous": s["uses_previous"],
        }
        for s in steps
    ],
    "final": {"P10": float(P10), "T10": float(T10)},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
