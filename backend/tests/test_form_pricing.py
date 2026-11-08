"""The list price is R$ 10 per new form, and it is not final."""

import pytest

from app.services.form_pricing import METHODS, UNIT_CENTS, UnknownPaymentMethod, quote_forms, require_method


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
