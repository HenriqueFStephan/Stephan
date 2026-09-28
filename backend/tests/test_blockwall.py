"""Maintenance wall gate."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1 import blockwall as blockwall_api
from app.main import app

client = TestClient(app)


class FakeSettings:
    def __init__(self, blockwall_key: str = "") -> None:
        self.blockwall_key = blockwall_key


def test_status_is_off_without_a_key(monkeypatch):
    monkeypatch.setattr(blockwall_api, "get_settings", lambda: FakeSettings(""))
    response = client.get("/api/v1/blockwall/status")
    assert response.status_code == 200
    assert response.json() == {"enabled": False}


def test_unlock_is_unavailable_without_a_key(monkeypatch):
    monkeypatch.setattr(blockwall_api, "get_settings", lambda: FakeSettings(""))
    response = client.post("/api/v1/blockwall/unlock", json={"password": "anything"})
    assert response.status_code == 404


def test_wrong_password_stays_locked(monkeypatch):
    monkeypatch.setattr(blockwall_api, "get_settings", lambda: FakeSettings("wall-secret"))
    response = client.post("/api/v1/blockwall/unlock", json={"password": "nope"})
    assert response.status_code == 401
    assert "passage" not in response.json()


def test_right_password_issues_a_passage_that_resumes(monkeypatch):
    monkeypatch.setattr(blockwall_api, "get_settings", lambda: FakeSettings("wall-secret"))
    unlocked = client.post("/api/v1/blockwall/unlock", json={"password": "wall-secret"})
    assert unlocked.status_code == 200
    body = unlocked.json()
    assert body["success"] is True
    assert body["passage"] != "wall-secret"

    resumed = client.post("/api/v1/blockwall/resume", json={"passage": body["passage"]})
    assert resumed.status_code == 200
    assert resumed.json() == {"success": True}

    rejected = client.post("/api/v1/blockwall/resume", json={"passage": "not-the-passage"})
    assert rejected.status_code == 401
