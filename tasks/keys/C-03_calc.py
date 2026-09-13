import json

P0 = 520.00
T0 = 24.00


def r2(x):
    return round(x, 2)


def r4(x):
    return round(x, 4)


steps = []

L1 = 0.90
P1 = r2(P0 * L1)
steps.append({"step": 1, "outputs": {"P1": P1}, "uses_previous": []})

K2 = 0.052
dT2 = r2(P1 * K2)
T2 = r2(T0 + dT2)
steps.append({"step": 2, "outputs": {"dT2": dT2, "T2": T2}, "uses_previous": ["P1"]})

F3 = r4(1 - r2(T2 - T0) * 0.0032)
P3 = r2(P1 * F3)
steps.append({"step": 3, "outputs": {"F3": F3, "P3": P3}, "uses_previous": ["T2", "P1"]})

K4 = 0.046
dT4 = r2(P3 * K4)
T4 = r2(T2 + dT4)
steps.append({"step": 4, "outputs": {"dT4": dT4, "T4": T4}, "uses_previous": ["P3", "T2"]})

F5 = r4(1 - r2(T4 - T0) * 0.0037)
P5 = r2(P3 * F5)
steps.append({"step": 5, "outputs": {"F5": F5, "P5": P5}, "uses_previous": ["T4", "P3"]})

K6 = 0.041
dT6 = r2(P5 * K6)
T6 = r2(T4 + dT6)
steps.append({"step": 6, "outputs": {"dT6": dT6, "T6": T6}, "uses_previous": ["P5", "T4"]})

F7 = r4(1 - r2(T6 - T0) * 0.0042)
P7 = r2(P5 * F7)
steps.append({"step": 7, "outputs": {"F7": F7, "P7": P7}, "uses_previous": ["T6", "P5"]})

K8 = 0.037
dT8 = r2(P7 * K8)
T8 = r2(T6 + dT8)
steps.append({"step": 8, "outputs": {"dT8": dT8, "T8": T8}, "uses_previous": ["P7", "T6"]})

F9 = r4(1 - r2(T8 - T0) * 0.0047)
P9 = r2(P7 * F9)
K9 = 0.033
dT9 = r2(P9 * K9)
T9 = r2(T8 + dT9)
steps.append({"step": 9, "outputs": {"F9": F9, "P9": P9, "dT9": dT9, "T9": T9}, "uses_previous": ["T8", "P7"]})

for s in steps:
    assert s["uses_previous"] or s["step"] == 1, s

result = {
    "task_id": "C-03",
    "chain_length": 9,
    "steps": steps,
    "final": {"P9": P9, "T9": T9},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
