"""Company portal login and the simulated HSE-IT reading."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.company_demo import ITEMS, cronbach_alpha, demo_overview

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
    assert sum(week["count"] for week in overview["weeks"]) == 100
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


def test_login_opens_the_overview(postgres):
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

    overview = client.get(
        "/api/v1/company/overview",
        headers={"X-Company-Token": passage},
    )
    assert overview.status_code == 200
    body = overview.json()
    assert body["respondent_count"] == 100
    assert body["company_id"] == "demo"
    assert body["latest_response_on"] >= body["first_response_on"]
    assert body["alpha"][0]["id"] == "overall"
