"""Group reading for one company round, from the forms stored for that round."""

from __future__ import annotations

from datetime import date, datetime

from app.services.campaign_store import ITEM_COLUMNS
from app.services.company_demo import build_overview, favourable_scores

# A smaller split can identify people. The page leaves it out.
MIN_SECTOR_SIZE = 5


def overview_for_round(conn, company_id, slug: str, label: str) -> dict | None:
    """Return the round's aggregate, or None when this company has no round with that label."""
    wave = conn.execute(
        """
        SELECT id
        FROM company_rounds
        WHERE company_id = %s
          AND label = %s
        """,
        (company_id, label),
    ).fetchone()
    if wave is None:
        return None
    rows = conn.execute(
        f"""
        SELECT submitted_on, economic_sector, {", ".join(ITEM_COLUMNS)}
        FROM hse_responses
        WHERE company_id = %s
          AND round_id = %s
        """,
        (company_id, wave["id"]),
    ).fetchall()
    people = []
    for row in rows:
        raw = [int(row[column]) for column in ITEM_COLUMNS]
        people.append(
            {
                "sector": row["economic_sector"] or "",
                "day": _as_date(row["submitted_on"]),
                "scores": favourable_scores(raw),
            }
        )
    return build_overview(
        people,
        source="recorded",
        company_id=slug,
        min_sector_size=MIN_SECTOR_SIZE,
    )


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
