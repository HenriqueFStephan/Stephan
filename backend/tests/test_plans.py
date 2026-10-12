"""Monthly fee bands stay aligned with the public plans table."""

import pytest

from app.services.plans import monthly_cents


def test_smaller_plan_steps_up_with_headcount():
    assert monthly_cents("hse", 1) == 69_000
    assert monthly_cents("hse", 49) == 69_000
    assert monthly_cents("hse", 50) == 129_000
    assert monthly_cents("hse", 199) == 129_000
    assert monthly_cents("hse", 200) == 219_000
    assert monthly_cents("hse", 499) == 219_000
    assert monthly_cents("hse", 500) == 349_000
    assert monthly_cents("hse", 1_000_000) == 349_000


def test_larger_plan_is_above_the_smaller_one_in_every_band():
    assert monthly_cents("analise", 49) == 149_000
    assert monthly_cents("analise", 199) == 279_000
    assert monthly_cents("analise", 200) == 469_000
    assert monthly_cents("analise", 5_000) == 749_000
    assert monthly_cents("analise", 49) > monthly_cents("hse", 49)
    assert monthly_cents("analise", 500) > monthly_cents("hse", 500)


def test_unknown_plan_or_empty_headcount_is_rejected():
    with pytest.raises(ValueError):
        monthly_cents("ciclo", 40)
    with pytest.raises(ValueError):
        monthly_cents("hse", 0)
