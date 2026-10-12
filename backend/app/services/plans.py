"""Monthly fees by plan and headcount.

Keep the cents identical to frontend/src/app/features/billing/plans.ts.
The order API rejects a quote that does not match this table.
"""

_BANDS: tuple[tuple[int | None, dict[str, int]], ...] = (
    (49, {"hse": 69_000, "analise": 149_000}),
    (199, {"hse": 129_000, "analise": 279_000}),
    (499, {"hse": 219_000, "analise": 469_000}),
    (None, {"hse": 349_000, "analise": 749_000}),
)


def monthly_cents(plan: str, headcount: int) -> int:
    if plan not in ("hse", "analise") or headcount < 1:
        raise ValueError("invalid monthly quote")
    for cap, amounts in _BANDS:
        if cap is None or headcount <= cap:
            return amounts["hse"] if plan == "hse" else amounts["analise"]
    raise ValueError("invalid monthly quote")
