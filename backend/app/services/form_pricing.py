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


class PaymentRequired(Exception):
    """A list with new forms is held until a method is confirmed."""


class SkipNotAllowed(Exception):
    """Only the internal admin company can release a list without a method."""


def require_method(method: str) -> str:
    code = method.strip()
    if code not in METHODS:
        raise UnknownPaymentMethod(code)
    return code


def gate_payment(slug: str, method: str, skip: bool, forms: int) -> str | None:
    """Return the method that releases the list, or None when there is nothing to pay.

    The internal company (slug ``internal``) may skip. That records no debit.
    """
    if skip:
        if slug != "internal":
            raise SkipNotAllowed()
        return None
    if forms <= 0:
        return None
    code = method.strip()
    if not code:
        raise PaymentRequired()
    return require_method(code)


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
