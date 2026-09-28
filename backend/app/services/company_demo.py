"""Simulated company reading for the portal.

One hundred anonymous HSE-IT forms. The item order and reverse flags match
frontend/src/app/features/tool/hse-it.ts. Percentile cuts match that file too.
This module is the test dataset described in docs/COMPANY_PORTAL.md.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache
from statistics import mean

# (dimension, reverse) in questionnaire order.
ITEMS: tuple[tuple[str, bool], ...] = (
    ("role", False),
    ("control", False),
    ("demands", True),
    ("role", False),
    ("relationships", True),
    ("demands", True),
    ("peer", False),
    ("manager", False),
    ("demands", True),
    ("control", False),
    ("role", False),
    ("demands", True),
    ("role", False),
    ("relationships", True),
    ("control", False),
    ("demands", True),
    ("role", False),
    ("demands", True),
    ("control", False),
    ("demands", True),
    ("relationships", True),
    ("demands", True),
    ("manager", False),
    ("peer", False),
    ("control", False),
    ("change", False),
    ("peer", False),
    ("change", False),
    ("manager", False),
    ("control", False),
    ("peer", False),
    ("change", False),
    ("manager", False),
    ("relationships", True),
    ("manager", False),
)

DIMENSION_ORDER: tuple[str, ...] = (
    "demands",
    "control",
    "manager",
    "peer",
    "relationships",
    "role",
    "change",
)

# HSE Analysis Tool organisational benchmark (136 organisations).
CUTS: dict[str, tuple[float, float, float]] = {
    "demands": (2.9387, 3.1024, 3.2937),
    "control": (3.224, 3.4741, 3.7208),
    "manager": (3.272, 3.4603, 3.65),
    "peer": (3.627, 3.78, 3.8892),
    "relationships": (3.6115, 3.8499, 4.0381),
    "role": (4.0356, 4.1803, 4.3117),
    "change": (2.791, 3.0428, 3.24),
}

# Latent favourable means, before sector and person shifts.
BASE: dict[str, float] = {
    "demands": 3.02,
    "control": 3.42,
    "manager": 3.40,
    "peer": 3.78,
    "relationships": 3.72,
    "role": 4.16,
    "change": 2.95,
}

# id, headcount, shift added to the favourable score (negative is less favourable).
SECTORS: tuple[tuple[str, int, dict[str, float]], ...] = (
    (
        "operation",
        34,
        {
            "demands": -0.28,
            "control": -0.22,
            "manager": -0.08,
            "peer": -0.05,
            "relationships": -0.18,
            "role": -0.04,
            "change": -0.12,
        },
    ),
    (
        "admin",
        28,
        {
            "demands": 0.18,
            "control": 0.16,
            "manager": 0.12,
            "peer": 0.08,
            "relationships": 0.10,
            "role": 0.06,
            "change": -0.08,
        },
    ),
    (
        "commercial",
        22,
        {
            "demands": -0.06,
            "control": 0.04,
            "manager": -0.04,
            "peer": 0.02,
            "relationships": -0.22,
            "role": 0.02,
            "change": 0.05,
        },
    ),
    (
        "care",
        16,
        {
            "demands": 0.05,
            "control": 0.02,
            "manager": 0.20,
            "peer": 0.14,
            "relationships": 0.06,
            "role": 0.04,
            "change": 0.10,
        },
    ),
)

WAVE_START = date(2026, 8, 3)
WAVE_END = date(2026, 9, 26)
DEMO_SEED = 20260928
DEMO_COMPANY_ID = "demo"


def sample_variance(values: list[float]) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    center = sum(values) / count
    return sum((value - center) ** 2 for value in values) / (count - 1)


def cronbach_alpha(rows: list[list[int]]) -> float | None:
    """Alpha on already-scored items. None when the scale cannot be estimated."""
    if len(rows) < 2:
        return None
    item_count = len(rows[0]) if rows else 0
    if item_count < 2 or any(len(row) != item_count for row in rows):
        return None
    item_vars = [
        sample_variance([float(row[index]) for row in rows]) for index in range(item_count)
    ]
    total_var = sample_variance([float(sum(row)) for row in rows])
    if total_var == 0:
        return None
    return (item_count / (item_count - 1)) * (1 - sum(item_vars) / total_var)


def alpha_reading(value: float | None) -> str:
    """Conventional bands for the coefficient. Not a risk rating."""
    if value is None:
        return "unknown"
    if value >= 0.9:
        return "excellent"
    if value >= 0.8:
        return "good"
    if value >= 0.7:
        return "acceptable"
    if value >= 0.6:
        return "questionable"
    return "weak"


def band_for(score: float, dimension: str) -> str:
    low, mid, high = CUTS[dimension]
    if score < low:
        return "urgent"
    if score < mid:
        return "improve"
    if score < high:
        return "good"
    return "maintain"


def _clamp_score(value: float) -> int:
    return min(5, max(1, int(round(value))))


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _favourable_rows() -> list[dict]:
    """One dict per person: sector, day, and 35 favourable scores in item order."""
    rng = random.Random(DEMO_SEED)
    slots: list[tuple[str, dict[str, float]]] = []
    for sector_id, count, shifts in SECTORS:
        slots.extend((sector_id, shifts) for _ in range(count))
    rng.shuffle(slots)

    span_days = (WAVE_END - WAVE_START).days
    people: list[dict] = []
    for sector_id, shifts in slots:
        general = rng.gauss(0, 0.22)
        dim_factor = {dimension: rng.gauss(0, 0.34) for dimension in DIMENSION_ORDER}
        scores: list[int] = []
        for dimension, _reverse in ITEMS:
            latent = (
                BASE[dimension]
                + shifts[dimension]
                + general
                + dim_factor[dimension]
                + rng.gauss(0, 0.22)
            )
            scores.append(_clamp_score(latent))
        day_offset = int(rng.random() * (span_days + 1))
        people.append(
            {
                "sector": sector_id,
                "day": WAVE_START + timedelta(days=day_offset),
                "scores": scores,
            }
        )
    return people


def _dimension_indexes() -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {dimension: [] for dimension in DIMENSION_ORDER}
    for index, (dimension, _reverse) in enumerate(ITEMS):
        grouped[dimension].append(index)
    return grouped


def _person_means(scores: list[int], indexes: dict[str, list[int]]) -> dict[str, float]:
    return {
        dimension: mean(scores[index] for index in item_indexes)
        for dimension, item_indexes in indexes.items()
    }


def _alpha_rows(people: list[dict], indexes: dict[str, list[int]]) -> list[dict]:
    rows = [person["scores"] for person in people]
    overall = cronbach_alpha(rows)
    payload = [
        {
            "id": "overall",
            "alpha": overall,
            "items": len(ITEMS),
            "n": len(people),
            "reading": alpha_reading(overall),
            "mean": None,
        }
    ]
    for dimension in DIMENSION_ORDER:
        item_indexes = indexes[dimension]
        matrix = [[person["scores"][index] for index in item_indexes] for person in people]
        value = cronbach_alpha(matrix)
        payload.append(
            {
                "id": dimension,
                "alpha": value,
                "items": len(item_indexes),
                "n": len(people),
                "reading": alpha_reading(value),
                "mean": mean(person_mean[dimension] for person_mean in (
                    _person_means(person["scores"], indexes) for person in people
                )),
            }
        )
    return payload


@lru_cache(maxsize=1)
def demo_overview() -> dict:
    """Aggregate reading. Individual forms are not part of the payload."""
    people = _favourable_rows()
    indexes = _dimension_indexes()
    person_means = [_person_means(person["scores"], indexes) for person in people]

    dimensions = []
    bands = []
    for dimension in DIMENSION_ORDER:
        values = [row[dimension] for row in person_means]
        dimensions.append({"id": dimension, "mean": mean(values)})
        counts = {"urgent": 0, "improve": 0, "good": 0, "maintain": 0}
        for value in values:
            counts[band_for(value, dimension)] += 1
        bands.append({"id": dimension, **counts})

    by_sector: dict[str, list[dict[str, float]]] = defaultdict(list)
    for person, scores in zip(people, person_means):
        by_sector[person["sector"]].append(scores)
    sectors = []
    for sector_id, _count, _shifts in SECTORS:
        group = by_sector[sector_id]
        sectors.append(
            {
                "id": sector_id,
                "count": len(group),
                "means": [
                    {"id": dimension, "mean": mean(row[dimension] for row in group)}
                    for dimension in DIMENSION_ORDER
                ],
            }
        )

    week_counts: dict[date, int] = defaultdict(int)
    for person in people:
        week_counts[_week_start(person["day"])] += 1
    first_week = _week_start(min(person["day"] for person in people))
    last_week = _week_start(max(person["day"] for person in people))
    weeks = []
    cursor = first_week
    while cursor <= last_week:
        weeks.append({"week": cursor.isoformat(), "count": week_counts[cursor]})
        cursor += timedelta(days=7)

    days = [person["day"] for person in people]
    return {
        "source": "simulated",
        "company_id": DEMO_COMPANY_ID,
        "respondent_count": len(people),
        "first_response_on": min(days).isoformat(),
        "latest_response_on": max(days).isoformat(),
        "alpha": _alpha_rows(people, indexes),
        "dimensions": dimensions,
        "sectors": sectors,
        "weeks": weeks,
        "bands": bands,
    }
