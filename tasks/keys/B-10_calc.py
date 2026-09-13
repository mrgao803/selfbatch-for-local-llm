import json
from decimal import Decimal, ROUND_HALF_UP


def rnd(value, places):
    q = Decimal(1).scaleb(-places)
    return value.quantize(q, rounding=ROUND_HALF_UP)


def d(x):
    return Decimal(str(x))


PARAMS = [
    {"step": 1, "H": d("7.2400"), "B": d("600000.00"), "s": d("0.1000"), "f": d("0.0040")},
    {"step": 2, "H": d("1.0800"), "B": d("85000.00"), "s": d("0.1200"), "f": d("0.0035")},
    {"step": 3, "H": d("1.1700"), "B": d("80000.00"), "s": d("0.0800"), "f": d("0.0030")},
    {"step": 4, "H": d("9.9000"), "B": d("65000.00"), "s": d("0.1500"), "f": d("0.0025")},
    {"step": 5, "H": d("1.0870"), "B": d("6600.00"), "s": d("0.0600"), "f": d("0.0020")},
]

M_prev = d("600000.00")

steps = []
for p in PARAMS:
    i = p["step"]
    D = (M_prev - p["B"]) / p["B"]
    E = rnd(p["H"] * (1 + p["s"] * D), 4)
    F = rnd(M_prev * p["f"], 2)
    N = M_prev - F
    M = rnd(N / E, 2)
    steps.append({
        "step": i,
        "outputs": {
            "D%d" % i: float(rnd(D, 6)),
            "E%d" % i: float(E),
            "F%d" % i: float(F),
            "N%d" % i: float(N),
            "M%d" % i: float(M),
        },
        "uses_previous": [] if i == 1 else ["M%d" % (i - 1)],
    })
    M_prev = M

result = {
    "task_id": "B-10",
    "chain_length": 5,
    "steps": steps,
    "final": {"M5": float(M_prev)},
}

print(json.dumps(result, ensure_ascii=False, indent=2))
