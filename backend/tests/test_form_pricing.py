"""The list price is R$ 10 per new form, and it is not final."""

import pytest

from app.services.form_pricing import (
    METHODS,
    UNIT_CENTS,
    PaymentRequired,
    SkipNotAllowed,
    UnknownPaymentMethod,
    gate_payment,
    quote_forms,
    require_method,
)


def test_three_forms_cost_thirty_reais_and_nothing_is_charged():
    quote = quote_forms(3)
    assert UNIT_CENTS == 1_000
    assert quote["forms"] == 3
    assert quote["unit_cents"] == 1_000
    assert quote["total_cents"] == 3_000
    assert quote["provisional"] is True
    assert quote["charged"] is False
    assert quote["method"] is None
    assert quote["methods"] == list(METHODS)


def test_a_negative_count_is_priced_as_zero():
    assert quote_forms(0)["total_cents"] == 0
    assert quote_forms(-2)["forms"] == 0


def test_only_catalog_methods_can_be_chosen():
    assert require_method(" pix ") == "pix"
    with pytest.raises(UnknownPaymentMethod):
        require_method("cash")


def test_a_list_stays_held_until_payment_and_only_admin_can_skip():
    assert gate_payment("hse-it", "pix", False, 2) == "pix"
    assert gate_payment("internal", "", True, 2) is None
    assert gate_payment("hse-it", "", False, 0) is None
    with pytest.raises(PaymentRequired):
        gate_payment("hse-it", "", False, 2)
    with pytest.raises(SkipNotAllowed):
        gate_payment("hse-it", "", True, 2)
    with pytest.raises(UnknownPaymentMethod):
        gate_payment("internal", "cash", False, 1)
