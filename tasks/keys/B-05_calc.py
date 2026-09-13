import json
from decimal import Decimal, ROUND_HALF_UP

TASK_ID = "B-05"
CHAIN_LENGTH = 4
PRINCIPAL = Decimal("120000.00")
MONTHLY_PAYMENT = Decimal("12300.00")
MONTHLY_RATE = Decimal("0.0039")


def r2(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def main():
    steps = []
    remaining = PRINCIPAL
    for i in range(1, CHAIN_LENGTH + 1):
        interest = r2(remaining * MONTHLY_RATE)
        principal_part = r2(MONTHLY_PAYMENT - interest)
        new_remaining = r2(remaining - principal_part)
        steps.append({
            "step": i,
            "outputs": {
                "I%d" % i: float(interest),
                "B%d" % i: float(principal_part),
                "R%d" % i: float(new_remaining),
            },
            "uses_previous": [] if i == 1 else ["R%d" % (i - 1)],
        })
        remaining = new_remaining

    result = {
        "task_id": TASK_ID,
        "chain_length": CHAIN_LENGTH,
        "steps": steps,
        "final": dict(steps[-1]["outputs"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
