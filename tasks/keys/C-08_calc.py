#!/usr/bin/env python3
"""C-08 底稿答案：十一级压缩与损耗递推。

严格按 tasks/C-08.md 材料中的公式与参数逐级计算。
每一步使用上一步已取整的输出 S_{i-1} 与 T_{i-1}，链为真串行。
"""

import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "C-08"

S0 = Decimal("2048.00")
T0 = Decimal("0.00")

# 各级压缩比 r_i 与丢弃率 q_i（与材料逐字一致）
RATIOS = [
    "0.5000", "0.6250", "0.8000", "0.4500", "0.7500", "0.9000",
    "0.3500", "0.6000", "0.8500", "0.5500", "0.7000",
]
DROPS = [
    "0.0100", "0.0200", "0.0150", "0.0300", "0.0250", "0.0100",
    "0.0400", "0.0200", "0.0350", "0.0150", "0.0500",
]

assert len(RATIOS) == 11 and len(DROPS) == 11


def round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round4(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def f2(x: Decimal) -> float:
    return float(round2(x))


def f4(x: Decimal) -> float:
    return float(round4(x))


steps = []
prev_s = S0
prev_t = T0

for i in range(1, 12):
    r = Decimal(RATIOS[i - 1])
    q = Decimal(DROPS[i - 1])

    in_size = prev_s
    a_i = round2(in_size * r)
    w_i = round2(a_i * q)
    s_i = round2(a_i - w_i)
    u_i = round4(Decimal(1) - s_i / in_size)
    t_i = round2(prev_t + w_i)
    d_i = round4(t_i / S0)

    outputs = {
        f"IN{i}": f2(in_size),
        f"A{i}": f2(a_i),
        f"W{i}": f2(w_i),
        f"S{i}": f2(s_i),
        f"u{i}": f4(u_i),
        f"T{i}": f2(t_i),
        f"D{i}": f4(d_i),
    }
    uses_previous = [] if i == 1 else [f"S{i-1}", f"T{i-1}"]

    steps.append({"step": i, "outputs": outputs, "uses_previous": uses_previous})

    prev_s = s_i
    prev_t = t_i

final = {
    "S11": f2(prev_s),
    "T11": f2(prev_t),
    "D11": f4(prev_t / S0),
}

result = {
    "task_id": TASK_ID,
    "chain_length": 11,
    "steps": steps,
    "final": final,
}

# 自检：第 2 步起每步必须有非空的 uses_previous
for st in result["steps"]:
    if st["step"] != 1 and not st["uses_previous"]:
        raise SystemExit(f"步骤 {st['step']} 不依赖上一步，分类错误")

print(json.dumps(result, ensure_ascii=False, indent=2))
