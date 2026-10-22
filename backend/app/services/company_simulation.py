"""Three closed rounds of simulated forms for the internal admin company.

The rows are ordinary campaign data: rounds, invitations, and anonymous answers.
The company page reads them the same way it reads any other company. A second
call does not add another copy.
"""

from __future__ import annotations

import hashlib
import random
import secrets
from datetime import date, datetime, time, timedelta
from uuid import uuid4

from app.services.campaign_store import record_response
from app.services.company_demo import BASE, DIMENSION_ORDER, ITEMS, _clamp_score

AGE_BANDS = ("18_24", "25_34", "35_44", "45_54", "55_64", "65_plus")

# Earlier seeds used the month name. The open round from the schema is rodada-1.
LEGACY_LABELS = {
    "Março 2026": "1",
    "Junho 2026": "2",
    "Setembro 2026": "3",
    "rodada-1": "4",
}

# The first seed closed each round after a few weeks. Answers now run longer.
PRIOR_CLOSED = {
    "1": date(2026, 3, 27),
    "2": date(2026, 6, 26),
    "3": date(2026, 9, 25),
}

# label, window, how many invitations are still waiting, sector sizes, favourable shifts.
SIMULATED_ROUNDS: tuple[dict, ...] = (
    {
        "label": "1",
        "slug": "marco-2026",
        "opened_on": date(2026, 3, 2),
        "closed_on": date(2026, 5, 22),
        "seed": 20260302,
        "waiting": 12,
        "sectors": (("manufacturing", 12), ("services", 10), ("retail", 8), ("health", 6)),
        "shifts": {"demands": 0.16, "control": 0.08, "change": 0.06},
    },
    {
        "label": "2",
        "slug": "junho-2026",
        "opened_on": date(2026, 6, 1),
        "closed_on": date(2026, 8, 21),
        "seed": 20260601,
        "waiting": 24,
        "sectors": (
            ("manufacturing", 16),
            ("services", 14),
            ("retail", 12),
            ("health", 8),
            ("education", 6),
        ),
        "shifts": {"demands": -0.06, "relationships": -0.08},
    },
    {
        "label": "3",
        "slug": "setembro-2026",
        "opened_on": date(2026, 9, 1),
        "closed_on": date(2026, 9, 30),
        "seed": 20260901,
        "waiting": 36,
        "sectors": (
            ("manufacturing", 22),
            ("services", 18),
            ("retail", 16),
            ("health", 12),
            ("education", 10),
            ("it", 6),
        ),
        "shifts": {"demands": -0.22, "control": -0.1, "change": -0.14},
    },
)


def answered_count(spec: dict) -> int:
    return sum(count for _sector, count in spec["sectors"])


def _spread_answers(conn, company_id, spec: dict) -> None:
    """Place this round's simulated forms on scattered days, and lengthen a short close."""
    wave = conn.execute(
        """
        SELECT id, closed_on
        FROM company_rounds
        WHERE company_id = %s AND label = %s
        """,
        (company_id, spec["label"]),
    ).fetchone()
    if wave is None:
        return
    closed = wave["closed_on"]
    if isinstance(closed, datetime):
        closed = closed.date()
    prior = PRIOR_CLOSED.get(spec["label"])
    if prior is not None and closed == prior:
        conn.execute(
            "UPDATE company_rounds SET closed_on = %s WHERE id = %s",
            (spec["closed_on"], wave["id"]),
        )
    rows = conn.execute(
        "SELECT id FROM hse_responses WHERE round_id = %s ORDER BY id",
        (wave["id"],),
    ).fetchall()
    expected = answered_count(spec)
    if len(rows) != expected:
        return
    for row, day in zip(rows, _scattered_days(spec, expected)):
        conn.execute(
            "UPDATE hse_responses SET submitted_on = %s WHERE id = %s",
            (day, row["id"]),
        )


def _scattered_days(spec: dict, count: int) -> list[date]:
    """A few active days across the round. The days between them stay empty."""
    rng = random.Random(spec["seed"] + 17)
    start = spec["opened_on"]
    span = (spec["closed_on"] - start).days
    if span < 1 or count < 1:
        return [start] * count
    early = min(5, span // 6)
    late = max(early + 1, span - min(7, span // 6))
    active = max(6, min(count, max(3, span // 5)))
    anchors = {early, (early + late) // 2, late}
    active = min(span + 1, max(active, len(anchors)))
    pool = [offset for offset in range(span + 1) if offset not in anchors]
    picked = set(anchors)
    extra = active - len(picked)
    if extra > 0 and pool:
        picked.update(rng.sample(pool, min(extra, len(pool))))
    offsets = sorted(picked)
    if len(offsets) > count:
        offsets = offsets[:count]
    base, remainder = divmod(count, len(offsets))
    days: list[date] = []
    for index, offset in enumerate(offsets):
        days.extend([start + timedelta(days=offset)] * (base + (1 if index < remainder else 0)))
    rng.shuffle(days)
    return days


def seed_admin_rounds(conn) -> None:
    """Insert the three admin rounds when they are missing. Does not commit."""
    company = conn.execute("SELECT id FROM companies WHERE slug = 'internal'").fetchone()
    if company is None:
        return
    company_id = company["id"]
    for old, new in LEGACY_LABELS.items():
        conn.execute(
            """
            UPDATE company_rounds
            SET label = %s
            WHERE company_id = %s
              AND label = %s
              AND NOT EXISTS (
                SELECT 1 FROM company_rounds
                WHERE company_id = %s AND label = %s
              )
            """,
            (new, company_id, old, company_id, new),
        )
    for spec in SIMULATED_ROUNDS:
        existing = conn.execute(
            """
            SELECT id FROM company_rounds
            WHERE company_id = %s AND label = %s
            """,
            (company_id, spec["label"]),
        ).fetchone()
        if existing is None:
            _insert_round(conn, company_id, spec)
        _spread_answers(conn, company_id, spec)


def _insert_round(conn, company_id, spec: dict) -> None:
    round_id = uuid4()
    upload_id = uuid4()
    conn.execute(
        """
        INSERT INTO company_rounds (id, company_id, label, opened_on, closed_on)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (round_id, company_id, spec["label"], spec["opened_on"], spec["closed_on"]),
    )
    conn.execute(
        """
        INSERT INTO invitation_uploads (id, company_id, round_id, source_name, format)
        VALUES (%s, %s, %s, %s, 'csv')
        """,
        (upload_id, company_id, round_id, f"{spec['slug']}.csv"),
    )
    people = _people(spec)
    for index, person in enumerate(people):
        _insert_invitation(
            conn,
            company_id=company_id,
            round_id=round_id,
            upload_id=upload_id,
            email=f"sim-{spec['slug']}-{index:03d}@example.invalid",
            sent_on=spec["opened_on"],
            submitted_on=person["day"],
        )
        record_response(
            conn,
            company_id=company_id,
            round_id=round_id,
            submitted_on=person["day"],
            demographics={
                "age_band": AGE_BANDS[index % len(AGE_BANDS)],
                "economic_sector": person["sector"],
            },
            answers=person["raw"],
        )
    for index in range(spec["waiting"]):
        _insert_invitation(
            conn,
            company_id=company_id,
            round_id=round_id,
            upload_id=upload_id,
            email=f"sim-{spec['slug']}-wait-{index:03d}@example.invalid",
            sent_on=spec["opened_on"],
            submitted_on=None,
        )


def _insert_invitation(
    conn,
    *,
    company_id,
    round_id,
    upload_id,
    email: str,
    sent_on: date,
    submitted_on: date | None,
) -> None:
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    submitted_at = datetime.combine(submitted_on, time(12, 0)) if submitted_on else None
    conn.execute(
        """
        INSERT INTO invitations (
            id, company_id, round_id, upload_id, email,
            link_token, link_token_hash, status, submitted_at, sent_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            uuid4(),
            company_id,
            round_id,
            upload_id,
            email,
            token,
            digest,
            "submitted" if submitted_on else "pending",
            submitted_at,
            datetime.combine(sent_on, time(8, 0)),
        ),
    )


def _people(spec: dict) -> list[dict]:
    """Favourable scores drawn like the demo wave, stored later as raw marks."""
    rng = random.Random(spec["seed"])
    slots: list[str] = []
    for sector, count in spec["sectors"]:
        slots.extend([sector] * count)
    rng.shuffle(slots)
    start = spec["opened_on"]
    span = (spec["closed_on"] - start).days
    shifts = spec["shifts"]
    people = []
    for sector in slots:
        general = rng.gauss(0, 0.2)
        dim_factor = {dimension: rng.gauss(0, 0.3) for dimension in DIMENSION_ORDER}
        favourable: list[int] = []
        for dimension, _reverse in ITEMS:
            latent = (
                BASE[dimension]
                + shifts.get(dimension, 0.0)
                + general
                + dim_factor[dimension]
                + rng.gauss(0, 0.18)
            )
            favourable.append(_clamp_score(latent))
        day_offset = int(rng.random() * (span + 1))
        people.append(
            {
                "sector": sector,
                "day": start + timedelta(days=day_offset),
                "raw": [6 - score if reverse else score for score, (_dimension, reverse) in zip(favourable, ITEMS)],
            }
        )
    return people
