"""Company portal login and the HSE-IT group reading."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import connect
from app.main import app
from app.services.campaign_store import record_response
from app.services.company_demo import (
    DIMENSION_ORDER,
    ITEMS,
    build_overview,
    cronbach_alpha,
    demo_overview,
    favourable_scores,
)

client = TestClient(app)


def test_cronbach_is_one_when_items_move_together():
    rows = [[1, 1], [2, 2], [3, 3], [4, 4]]
    assert cronbach_alpha(rows) == 1


def test_cronbach_is_undefined_without_variation():
    assert cronbach_alpha([[1, 5], [2, 4], [3, 3]]) is None
    assert cronbach_alpha([[1, 2]]) is None
    assert cronbach_alpha([[1], [2], [3]]) is None


def test_simulated_wave_has_one_hundred_forms():
    overview = demo_overview()
    assert overview["source"] == "simulated"
    assert overview["respondent_count"] == 100
    assert len(ITEMS) == 35
    assert sum(1 for _dimension, reverse in ITEMS if reverse) == 12
    assert sum(sector["count"] for sector in overview["sectors"]) == 100
    assert sum(day["count"] for day in overview["days"]) == 100
    for band in overview["bands"]:
        assert band["urgent"] + band["improve"] + band["good"] + band["maintain"] == 100
    overall = overview["alpha"][0]
    assert overall["id"] == "overall"
    assert overall["n"] == 100
    assert overall["items"] == 35
    assert overall["alpha"] is not None
    assert 0.7 < overall["alpha"] < 1
    assert "answers" not in overview


def test_login_rejects_a_wrong_password(postgres):
    response = client.post(
        "/api/v1/company/login",
        json={"username": "admin", "password": "nope"},
    )
    assert response.status_code == 401
    assert "passage" not in response.json()


def test_received_days_include_the_gaps_between_first_and_last():
    scores = favourable_scores([1] * 35)
    people = [
        {"sector": "health", "day": date(2026, 8, 4), "scores": scores}
        for _ in range(5)
    ]
    people.append({"sector": "retail", "day": date(2026, 8, 12), "scores": scores})
    people.append({"sector": "retail", "day": date(2026, 9, 1), "scores": scores})
    overview = build_overview(
        people,
        source="recorded",
        company_id="internal",
        min_sector_size=5,
    )
    assert overview["respondent_count"] == 7
    assert overview["source"] == "recorded"
    days = overview["days"]
    assert days[0]["day"] == "2026-08-04"
    assert days[-1]["day"] == "2026-09-01"
    assert len(days) == (date(2026, 9, 1) - date(2026, 8, 4)).days + 1
    assert sum(day["count"] for day in days) == 7
    assert any(day["count"] == 0 for day in days)
    assert days[0]["count"] == 5
    assert [sector["id"] for sector in overview["sectors"]] == ["health"]
    expected = {}
    for dimension in DIMENSION_ORDER:
        marks = [6 - 1 if reverse else 1 for item_dimension, reverse in ITEMS if item_dimension == dimension]
        expected[dimension] = sum(marks) / len(marks)
    for row in overview["dimensions"]:
        assert row["mean"] == expected[row["id"]]
    assert "answers" not in overview

    empty = build_overview(
        [],
        source="recorded",
        company_id="internal",
        min_sector_size=5,
    )
    assert empty["respondent_count"] == 0
    assert empty["first_response_on"] is None
    assert empty["dimensions"] == []
    assert empty["days"] == []


def test_admin_simulation_is_three_company_rounds(postgres):
    from app.services.company_simulation import SIMULATED_ROUNDS, answered_count, seed_admin_rounds

    with connect() as conn:
        seed_admin_rounds(conn)
        seed_admin_rounds(conn)
        conn.commit()

    logged_in = client.post(
        "/api/v1/company/login",
        json={"username": "admin", "password": "admintest"},
    )
    headers = {"X-Company-Token": logged_in.json()["passage"]}
    listed = client.get("/api/v1/company/rounds", headers=headers)
    assert listed.status_code == 200
    rounds = {row["label"]: row for row in listed.json()}
    assert "example.invalid" not in listed.text
    for spec in SIMULATED_ROUNDS:
        row = rounds[spec["label"]]
        assert row["closed_on"] == spec["closed_on"].isoformat()
        assert row["invited"] == answered_count(spec) + spec["waiting"]
        assert row["responded_percent"] + row["waiting_percent"] == 100
        overview = client.get(
            "/api/v1/company/overview",
            params={"round": spec["label"]},
            headers=headers,
        )
        assert overview.status_code == 200
        body = overview.json()
        assert body["source"] == "recorded"
        assert body["company_id"] == "internal"
        assert body["respondent_count"] == answered_count(spec)
        received = body["days"]
        assert received[0]["day"] == body["first_response_on"]
        assert received[-1]["day"] == body["latest_response_on"]
        span = date.fromisoformat(received[-1]["day"]) - date.fromisoformat(received[0]["day"])
        assert len(received) == span.days + 1
        assert sum(day["count"] for day in received) == answered_count(spec)
        assert any(day["count"] == 0 for day in received)
        assert body["sectors"]
        assert all(sector["count"] >= 5 for sector in body["sectors"])
        assert "@" not in overview.text

    artigo = client.post(
        "/api/v1/company/login",
        json={"username": "artigo", "password": "voltarassamambanhas"},
    )
    other = client.get(
        "/api/v1/company/overview",
        params={"round": SIMULATED_ROUNDS[0]["label"]},
        headers={"X-Company-Token": artigo.json()["passage"]},
    )
    assert other.status_code == 404


def test_login_does_not_open_the_shared_demo(postgres):
    logged_in = client.post(
        "/api/v1/company/login",
        json={"username": "admin", "password": "admintest"},
    )
    assert logged_in.status_code == 200
    body = logged_in.json()
    passage = body["passage"]
    assert passage != "admintest"
    assert body["company_slug"] == "internal"
    assert body["company_name"] == "Uso interno"

    missing = client.get("/api/v1/company/overview")
    assert missing.status_code == 401

    unscoped = client.get(
        "/api/v1/company/overview",
        headers={"X-Company-Token": passage},
    )
    assert unscoped.status_code == 422


def test_overview_is_the_signed_in_companys_round(postgres):
    logged_in = client.post(
        "/api/v1/company/login",
        json={"username": "admin", "password": "admintest"},
    )
    headers = {"X-Company-Token": logged_in.json()["passage"]}
    round_id = None
    response_id = None
    label = ""
    try:
        with connect() as conn:
            company = conn.execute("SELECT id FROM companies WHERE slug = 'internal'").fetchone()
            round_id = uuid4()
            label = f"rodada-{round_id.hex[:8]}"
            conn.execute(
                """
                INSERT INTO company_rounds (id, company_id, label, opened_on, closed_on)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (round_id, company["id"], label, date(2026, 8, 3), date(2026, 8, 16)),
            )
            response_id = record_response(
                conn,
                company_id=company["id"],
                round_id=round_id,
                submitted_on=date(2026, 8, 4),
                demographics={"age_band": "35_44", "economic_sector": "health"},
                answers=[1] * 35,
            )
            conn.commit()

        missing = client.get(
            "/api/v1/company/overview",
            params={"round": "rodada-inexistente"},
            headers=headers,
        )
        assert missing.status_code == 404

        overview = client.get(
            "/api/v1/company/overview",
            params={"round": label},
            headers=headers,
        )
        assert overview.status_code == 200
        body = overview.json()
        assert body["source"] == "recorded"
        assert body["company_id"] == "internal"
        assert body["respondent_count"] == 1
        assert body["sectors"] == []
        assert body["days"] == [{"day": "2026-08-04", "count": 1}]
        assert "email" not in overview.text
        assert "@" not in overview.text

        artigo = client.post(
            "/api/v1/company/login",
            json={"username": "artigo", "password": "voltarassamambanhas"},
        )
        other = client.get(
            "/api/v1/company/overview",
            params={"round": label},
            headers={"X-Company-Token": artigo.json()["passage"]},
        )
        assert other.status_code == 404
    finally:
        with connect() as conn:
            if response_id is not None:
                conn.execute("DELETE FROM hse_responses WHERE id = %s", (response_id,))
            if round_id is not None:
                conn.execute("DELETE FROM company_rounds WHERE id = %s", (round_id,))
            conn.commit()
