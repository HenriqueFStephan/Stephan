"""Campaign schema boundaries, and the upload API."""

from __future__ import annotations

import re
from pathlib import Path
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SCHEMA_PATH, DatabaseUnavailable, connect, ensure_schema
from app.main import app
from app.services.campaign_store import (
    BLOCKED_DEMOGRAPHIC_KEYS,
    DemographicRejected,
    clean_demographics,
    record_response,
)

ROOT = Path(__file__).resolve().parents[2]
LOCAL_URL = "postgresql://stephan:stephan@127.0.0.1:5432/stephan"


def test_answer_table_has_no_path_back_to_the_invitation():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    body = sql.split("CREATE TABLE IF NOT EXISTS hse_responses", 1)[1]
    body = body.split("CREATE INDEX IF NOT EXISTS hse_responses_round", 1)[0]
    assert "REFERENCES invitations" not in body
    columns = re.findall(r"^\s{4}([a-z][a-z0-9_]*)\s+", body, re.M)
    assert "email" not in columns
    assert "link_token" not in columns
    assert "invitation_id" not in columns
    assert "ip" not in columns
    assert columns.count("i01") == 1
    assert "i35" in columns
    assert "demographics" in columns


def test_blocked_demographic_keys_match_the_schema():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    array = re.search(r"jsonb_exists_any\(\s*demographics,\s*ARRAY\[(.*?)\]\s*\)", sql, re.S)
    assert array is not None
    keys = set(re.findall(r"'((?:[^']|'')*)'", array.group(1)))
    assert keys == set(BLOCKED_DEMOGRAPHIC_KEYS)


def test_demographics_stay_open_and_reject_identifiers():
    assert clean_demographics({}) == {}
    assert clean_demographics({"Age": 42, "Sex": "feminino"}) == {"age": 42, "sex": "feminino"}
    with pytest.raises(DemographicRejected):
        clean_demographics({"nome": "Ada"})
    with pytest.raises(DemographicRejected):
        clean_demographics({"job_title": "analista"})
    with pytest.raises(DemographicRejected):
        clean_demographics({"note": {"nested": True}})


def test_tool_stays_out_of_the_public_menu_and_footer():
    header = (ROOT / "frontend/src/app/shared/header/header.component.ts").read_text(encoding="utf-8")
    footer = (ROOT / "frontend/src/app/shared/footer/footer.component.ts").read_text(encoding="utf-8")
    assert "/tool" not in header
    assert "/tool" not in footer
    assert 'routerLink="/empresa"' in footer


def test_upload_rejects_a_name_column_without_a_database():
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    passage = logged.json()["passage"]
    response = client.post(
        "/api/v1/company/invitations",
        headers={"X-Company-Token": passage},
        files={"file": ("people.csv", b"email,nome\nada@example.com,Ada\n", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unknown_columns"
    assert response.json()["detail"]["columns"] == ["nome"]


def test_upload_requires_the_company_session():
    client = TestClient(app)
    response = client.post(
        "/api/v1/company/invitations",
        files={"file": ("people.csv", b"email\nada@example.com\n", "text/csv")},
    )
    assert response.status_code == 401


def test_upload_reports_database_unavailable_for_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/stephan.db")
    get_settings.cache_clear()
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    response = client.post(
        "/api/v1/company/invitations",
        headers={"X-Company-Token": logged.json()["passage"]},
        files={"file": ("people.csv", "email\nada@example.com\n", "text/csv")},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    get_settings.cache_clear()


def test_upload_without_smtp_does_not_keep_the_address(postgres, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_USERNAME", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    get_settings.cache_clear()
    email = f"pytest-{uuid4().hex}@example.com"
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    response = client.post(
        "/api/v1/company/invitations",
        headers={"X-Company-Token": logged.json()["passage"]},
        files={"file": ("pytest.csv", f"email\n{email}\n".encode(), "text/csv")},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "mail_not_configured"
    with connect() as conn:
        found = conn.execute("SELECT 1 FROM invitations WHERE email = %s", (email,)).fetchone()
        assert found is None
    get_settings.cache_clear()


@pytest.fixture
def postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", LOCAL_URL)
    get_settings.cache_clear()
    import app.db.session as session

    session._schema_ready = False
    try:
        with connect() as conn:
            ensure_schema(conn)
            conn.execute("SELECT 1")
    except DatabaseUnavailable:
        get_settings.cache_clear()
        pytest.skip("local PostgreSQL is not running")
    yield
    get_settings.cache_clear()


def test_upload_dedupes_against_the_open_round_and_answers_stay_anonymous(postgres, monkeypatch):
    email = f"pytest-{uuid4().hex}@example.com"
    sent: list[tuple[str, str]] = []

    def fake_deliver(pairs: list[tuple[str, str]]):
        sent.extend(pairs)
        return list(pairs), []

    monkeypatch.setattr("app.services.campaign_store.deliver_invitations", fake_deliver)
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    passage = logged.json()["passage"]
    headers = {"X-Company-Token": passage}
    body = f"email\n{email}\n\n{email}\n".encode()

    with connect() as conn:
        before_invites = _ids(conn, "invitations")
        before_uploads = _ids(conn, "invitation_uploads")
        before_answers = _ids(conn, "hse_responses")

    try:
        first = client.post(
            "/api/v1/company/invitations",
            headers=headers,
            files={"file": ("pytest.csv", body, "text/csv")},
        )
        assert first.status_code == 200
        saved = first.json()
        assert saved["accepted"] == 1
        assert saved["ignored_empty"] == 1
        assert saved["duplicates_in_file"] == [email]
        assert saved["already_invited"] == []
        assert saved["not_sent"] == []
        assert "link_token" not in saved
        assert len(sent) == 1
        assert sent[0][0] == email
        assert sent[0][1] not in first.text

        second = client.post(
            "/api/v1/company/invitations",
            headers=headers,
            files={"file": ("pytest.csv", f"email\n{email}\n".encode(), "text/csv")},
        )
        assert second.status_code == 200
        assert second.json()["accepted"] == 0
        assert second.json()["already_invited"] == [email]
        assert len(sent) == 1

        roster = client.get("/api/v1/company/invitations", headers=headers)
        assert roster.status_code == 200
        with connect() as conn:
            stored_status = conn.execute(
                "SELECT status FROM invitations WHERE email = %s",
                (email,),
            ).fetchone()
            others = conn.execute(
                "SELECT count(*) AS n FROM invitations WHERE email <> %s",
                (email,),
            ).fetchone()
        assert stored_status["status"] == "pending"
        progress = roster.json()
        assert progress["invited"] == int(others["n"]) + 1
        assert progress["responded_percent"] is not None
        assert progress["waiting_percent"] == 100 - progress["responded_percent"]
        assert email not in roster.text
        assert "pending" not in progress
        assert "submitted" not in progress

        with connect() as conn:
            columns = {
                row["column_name"]
                for row in conn.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'hse_responses'
                    """
                ).fetchall()
            }
            assert "email" not in columns
            assert "link_token" not in columns
            assert "invitation_id" not in columns
            response_id = record_response(
                conn,
                submitted_on=date(2026, 10, 1),
                demographics={"age": 40},
                answers=[3] * 35,
            )
            stored = conn.execute(
                "SELECT demographics FROM hse_responses WHERE id = %s",
                (response_id,),
            ).fetchone()
            assert stored["demographics"]["age"] == 40
            conn.commit()
    finally:
        with connect() as conn:
            new_answers = _ids(conn, "hse_responses") - before_answers
            new_invites = _ids(conn, "invitations") - before_invites
            new_uploads = _ids(conn, "invitation_uploads") - before_uploads
            if new_answers:
                conn.execute("DELETE FROM hse_responses WHERE id = ANY(%s)", (list(new_answers),))
            if new_invites:
                conn.execute("DELETE FROM invitations WHERE id = ANY(%s)", (list(new_invites),))
            if new_uploads:
                conn.execute("DELETE FROM invitation_uploads WHERE id = ANY(%s)", (list(new_uploads),))
            conn.commit()


def _ids(conn, table: str) -> set:
    if table not in {"invitations", "invitation_uploads", "hse_responses"}:
        raise AssertionError(table)
    return {row["id"] for row in conn.execute(f"SELECT id FROM {table}").fetchall()}
