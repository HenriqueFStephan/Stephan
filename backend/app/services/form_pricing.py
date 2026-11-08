"""Provisional price of one invitation list.

R$ 10 per form is a placeholder. It is not the published price.
The charge records the count and the method the company picked.
It does not debit, and it does not know a recipient account.
"""

from __future__ import annotations

UNIT_CENTS = 1_000

# Instruments a Brazilian service company can offer on a remote charge.
# The card number stays at the payment institution. A payment link is the
# institution's page, where the payer picks Pix, boleto, or card.
METHODS = (
    "pix",
    "pix_automatic",
    "boleto",
    "credit",
    "credit_installments",
    "debit",
    "payment_link",
    "ted",
)


class UnknownPaymentMethod(Exception):
    """The company picked a method that is not in the catalog."""

    def __init__(self, method: str) -> None:
        self.method = method
        super().__init__(method)


def require_method(method: str) -> str:
    code = method.strip()
    if code not in METHODS:
        raise UnknownPaymentMethod(code)
    return code


def quote_forms(forms: int, method: str | None = None) -> dict:
    count = forms if forms > 0 else 0
    return {
        "forms": count,
        "unit_cents": UNIT_CENTS,
        "total_cents": count * UNIT_CENTS,
        "provisional": True,
        "methods": list(METHODS),
        "method": method,
        "charged": False,
    }
