"""B-09 底稿答案：晨川 L5 产线五道工序良率与产出递推。

按 tasks/B-09.md 材料里的公式与精度逐段计算，结果以 JSON 打印到 stdout。
"""
import json
from decimal import Decimal, ROUND_HALF_UP

D = Decimal

# 基础参数（材料给定常数）
P0 = D("12000.00")
r = D("0.9600")

# 各道工序的良率修正因子 c 与良率联动系数 s
C = {1: D("0.9850"), 2: D("0.9800"), 3: D("0.9750"), 4: D("0.9700"), 5: D("0.9650")}
S = {1: None, 2: D("0.1500"), 3: D("0.2000"), 4: D("0.2500"), 5: D("0.3000")}

Q4 = D("0.0001")
Q2 = D("0.01")


def r4(x):
    return x.quantize(Q4, rounding=ROUND_HALF_UP)


def r2(x):
    return x.quantize(Q2, rounding=ROUND_HALF_UP)


def f4(x):
    return float(r4(x))


def f2(x):
    return float(r2(x))


steps = []
O_prev = None   # 上道工序产出量 O_{i-1}
y_prev = None   # 上道工序良率 y_{i-1}
Y_prev = None   # 上道工序累计直通率 Y_{i-1}

for i in range(1, 6):
    if i == 1:
        I_i = r2(P0)
        y_i = r4(r * C[1])
        uses_prev = []
    else:
        I_i = r2(O_prev)
        y_i = r4(r * C[i] * (D(1) - (D(1) - y_prev) * S[i]))
        uses_prev = [f"O{i-1}", f"y{i-1}", f"Y{i-1}"]

    O_i = r2(I_i * y_i)
    Y_i = r4(y_i) if i == 1 else r4(Y_prev * y_i)

    out = {
        f"I{i}": f2(I_i),
        f"y{i}": f4(y_i),
        f"O{i}": f2(O_i),
        f"Y{i}": f4(Y_i),
    }
    steps.append({"step": i, "outputs": out, "uses_previous": uses_prev})

    O_prev, y_prev, Y_prev = O_i, y_i, Y_i

result = {
    "task_id": "B-09",
    "chain_length": 5,
    "steps": steps,
    "final": {"O5": steps[-1]["outputs"]["O5"], "Y5": steps[-1]["outputs"]["Y5"]},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
