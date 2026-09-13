import json

TASK_ID = "C-02"

P0 = 0.2000
G = [2.4000, 2.2000, 1.9000, 2.6000, 1.8000, 2.5000, 2.0000, 2.3000]
K = [3.0000, 4.0000, 5.0000, 6.0000, 7.0000, 8.0000, 9.0000, 10.0000]

steps = []
p_prev = P0
for idx, (g, k) in enumerate(zip(G, K), start=1):
    a = round(g / (1 + p_prev / k), 4)
    p = round(p_prev * a, 4)
    uses = [] if idx == 1 else ["P%d" % (idx - 1)]
    steps.append(
        {
            "step": idx,
            "inputs": {"P%d" % (idx - 1): p_prev},
            "outputs": {"A%d" % idx: a, "P%d" % idx: p},
            "uses_previous": uses,
        }
    )
    p_prev = p

result = {
    "task_id": TASK_ID,
    "chain_length": len(steps),
    "steps": steps,
    "final": {"P8": p_prev, "T": round(p_prev / P0, 4)},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
