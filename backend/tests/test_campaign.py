"""Campaign schema boundaries, and the upload API."""

from __future__ import annotations

import hashlib
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
    DEMOGRAPHIC_FIELDS,
    REQUIRED_DEMOGRAPHIC_KEYS,
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


def test_draft_table_keeps_the_hash_and_not_the_person():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    body = sql.split("CREATE TABLE IF NOT EXISTS hse_drafts", 1)[1]
    body = body.split("CREATE TABLE IF NOT EXISTS company_users", 1)[0]
    assert "REFERENCES invitations" not in body
    columns = re.findall(r"^\s{4}([a-z][a-z0-9_]*)\s+", body, re.M)
    assert "email" not in columns
    assert "link_token" not in columns
    assert "invitation_id" not in columns
    assert "link_token_hash" in columns
    assert "i35" in columns
    responses = sql.split("CREATE TABLE IF NOT EXISTS hse_responses", 1)[1]
    responses = responses.split("CREATE INDEX IF NOT EXISTS hse_responses_round", 1)[0]
    assert "hse_drafts" not in responses
    assert "link_token_hash" not in responses


def test_a_draft_may_omit_required_demographics():
    assert clean_demographics({"age_band": "18_24"}, require_complete=False) == {"age_band": "18_24"}
    assert clean_demographics({}, require_complete=False) == {}


def test_demographics_are_the_annex_and_reject_identifiers():
    assert clean_demographics({"Age_Band": "35_44", "economic_sector": "Health", "Leadership": "yes"}) == {
        "age_band": "35_44",
        "economic_sector": "health",
        "leadership": "yes",
    }
    with pytest.raises(DemographicRejected):
        clean_demographics({})
    with pytest.raises(DemographicRejected):
        clean_demographics({"age_band": "35_44"})
    with pytest.raises(DemographicRejected):
        clean_demographics({"age_band": "35_44", "economic_sector": "health", "nome": "Ada"})
    with pytest.raises(DemographicRejected):
        clean_demographics({"age_band": "35_44", "economic_sector": "health", "job_title": "analista"})
    with pytest.raises(DemographicRejected):
        clean_demographics({"age_band": "35_44", "economic_sector": "health", "area": "expedição"})
    with pytest.raises(DemographicRejected):
        clean_demographics({"age_band": "35_44", "economic_sector": "nope"})
    with pytest.raises(DemographicRejected):
        clean_demographics({"age_band": "35_44", "economic_sector": "health", "note": {"nested": True}})


def test_annex_codes_match_the_schema_and_the_form():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    for column, values in DEMOGRAPHIC_FIELDS.items():
        bodies = re.findall(
            rf"CHECK \({column} IS NULL OR {column} IN \((.*?)\)\)",
            sql,
        )
        assert len(bodies) == 3
        for body in bodies:
            assert re.findall(r"'([^']*)'", body) == list(values)
    text = (ROOT / "frontend/src/app/features/tool/profile.ts").read_text(encoding="utf-8")
    questions = re.findall(
        r"\{\s*id: '(?P<id>[a-z0-9_]+)',\s*"
        r"required: (?P<required>true|false),\s*"
        r"pt: '(?P<pt>[^']*)',\s*"
        r"en: '(?P<en>[^']*)',\s*"
        r"options: \[(?P<options>.*?)\]\s*,?\s*\}",
        text,
        re.S,
    )
    assert [item[0] for item in questions] == list(DEMOGRAPHIC_FIELDS)
    for key, required, _pt, _en, options in questions:
        found = re.findall(r"id: '([a-z0-9_]+)'", options)
        assert found == list(DEMOGRAPHIC_FIELDS[key])
        assert (required == "true") is (key in REQUIRED_DEMOGRAPHIC_KEYS)


def test_tool_stays_out_of_the_public_menu_and_footer():
    header = (ROOT / "frontend/src/app/shared/header/header.component.ts").read_text(encoding="utf-8")
    footer = (ROOT / "frontend/src/app/shared/footer/footer.component.ts").read_text(encoding="utf-8")
    assert "/tool" not in header
    assert "/tool" not in footer
    assert 'routerLink="/empresa"' in header
    assert 'routerLink="/empresa"' not in footer
    assert 'routerLink="/abordagem"' not in footer


def test_upload_rejects_a_name_column_without_storing_it(postgres):
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


def test_upload_reports_database_unavailable_for_sqlite(postgres, monkeypatch):
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    passage = logged.json()["passage"]
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/stephan.db")
    get_settings.cache_clear()
    response = client.post(
        "/api/v1/company/invitations",
        headers={"X-Company-Token": passage},
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


def test_upload_dedupes_against_the_open_round_and_answers_stay_anonymous(postgres, monkeypatch):
    email = f"pytest-{uuid4().hex}@example.com"
    sent: list[tuple[str, str]] = []

    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)

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
                """
                SELECT count(*) AS n
                FROM invitations
                WHERE email <> %s
                  AND round_id = (
                    SELECT id FROM company_rounds
                    WHERE company_id = (
                      SELECT id FROM companies WHERE slug = 'internal'
                    )
                      AND closed_on IS NULL
                  )
                """,
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
            assert "age_band" in columns
            assert "economic_sector" in columns
            assert "region" in columns
            company = conn.execute("SELECT id FROM companies WHERE slug = 'internal'").fetchone()
            opened = conn.execute(
                """
                SELECT id FROM company_rounds
                WHERE company_id = %s AND closed_on IS NULL
                """,
                (company["id"],),
            ).fetchone()
            annex = {
                "age_band": "35_44",
                "gender": "female",
                "economic_sector": "health",
                "leadership": "no",
                "region": "southeast",
            }
            response_id = record_response(
                conn,
                company_id=company["id"],
                round_id=opened["id"],
                submitted_on=date(2026, 10, 1),
                demographics=annex,
                answers=[3] * 35,
            )
            refused = client.post(
                "/api/v1/tool/responses",
                json={"token": sent[0][1], "answers": [3] * 35, "demographics": {}},
            )
            assert refused.status_code == 400
            assert refused.json()["detail"]["code"] == "demographics"
            saved = client.post(
                "/api/v1/tool/responses",
                json={"token": sent[0][1], "answers": [3] * 35, "demographics": annex},
            )
            assert saved.status_code == 200
            assert sent[0][1] not in saved.text
            again = client.post(
                "/api/v1/tool/responses",
                json={"token": sent[0][1], "answers": [3] * 35, "demographics": {}},
            )
            assert again.status_code == 409
            artigo = client.post(
                "/api/v1/company/login",
                json={"username": "artigo", "password": "voltarassamambanhas"},
            )
            assert artigo.status_code == 200
            assert artigo.json()["company_slug"] == "hse-it"
            other = client.get(
                "/api/v1/company/invitations",
                headers={"X-Company-Token": artigo.json()["passage"]},
            )
            assert other.status_code == 200
            assert other.json()["invited"] == 0
            assert email not in other.text
            listed = client.get("/api/v1/company/rounds", headers=headers)
            assert listed.status_code == 200
            waves = listed.json()
            current = next(row for row in waves if row["closed_on"] is None)
            assert current["invited"] >= 1
            assert current["responded_percent"] + current["waiting_percent"] == 100
            assert current["opened_on"]
            assert current["latest_response_on"]
            assert email not in listed.text
            assert "@" not in listed.text
            other_rounds = client.get(
                "/api/v1/company/rounds",
                headers={"X-Company-Token": artigo.json()["passage"]},
            )
            assert other_rounds.status_code == 200
            assert email not in other_rounds.text
            assert all(row["invited"] == 0 for row in other_rounds.json())
            stored = conn.execute(
                """
                SELECT demographics, age_band, gender, economic_sector, education, leadership, region
                FROM hse_responses WHERE id = %s
                """,
                (response_id,),
            ).fetchone()
            assert stored["demographics"]["age_band"] == "35_44"
            assert stored["age_band"] == "35_44"
            assert stored["gender"] == "female"
            assert stored["economic_sector"] == "health"
            assert stored["leadership"] == "no"
            assert stored["region"] == "southeast"
            assert stored["education"] is None
            posted_ids = _ids(conn, "hse_responses") - before_answers - {response_id}
            assert len(posted_ids) == 1
            posted = conn.execute(
                """
                SELECT age_band, economic_sector
                FROM hse_responses
                WHERE id = %s
                """,
                (posted_ids.pop(),),
            ).fetchone()
            assert posted["age_band"] == "35_44"
            assert posted["economic_sector"] == "health"
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


def test_a_refused_send_keeps_the_address_and_the_same_link(postgres, monkeypatch):
    email = f"pytest-{uuid4().hex}@example.com"
    calls: list[list[tuple[str, str]]] = []

    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)

    def fake_deliver(pairs: list[tuple[str, str]]):
        calls.append(list(pairs))
        if len(calls) == 1:
            return [], [pair[0] for pair in pairs]
        return list(pairs), []

    monkeypatch.setattr("app.services.campaign_store.deliver_invitations", fake_deliver)
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    headers = {"X-Company-Token": logged.json()["passage"]}
    with connect() as conn:
        before_invites = _ids(conn, "invitations")
        before_uploads = _ids(conn, "invitation_uploads")
    try:
        first = client.post(
            "/api/v1/company/invitations",
            headers=headers,
            files={"file": ("pytest.csv", f"email\n{email}\n".encode(), "text/csv")},
        )
        assert first.status_code == 200
        assert first.json()["accepted"] == 0
        assert first.json()["not_sent"] == [email]
        with connect() as conn:
            stored = conn.execute(
                "SELECT link_token, sent_at FROM invitations WHERE email = %s",
                (email,),
            ).fetchone()
        assert stored["sent_at"] is None
        roster = client.get("/api/v1/company/invitations", headers=headers)
        assert email in roster.json()["unsent"]
        again = client.post("/api/v1/company/invitations/retry", headers=headers)
        assert again.status_code == 200
        assert again.json()["sent"] == 1
        assert again.json()["not_sent"] == []
        assert calls[1][0][1] == stored["link_token"]
        assert stored["link_token"] not in again.text
        with connect() as conn:
            marked = conn.execute(
                "SELECT sent_at FROM invitations WHERE email = %s",
                (email,),
            ).fetchone()
        assert marked["sent_at"] is not None
        quiet = client.get("/api/v1/company/invitations", headers=headers)
        assert email not in quiet.json()["unsent"]
    finally:
        with connect() as conn:
            new_invites = _ids(conn, "invitations") - before_invites
            new_uploads = _ids(conn, "invitation_uploads") - before_uploads
            if new_invites:
                conn.execute("DELETE FROM invitations WHERE id = ANY(%s)", (list(new_invites),))
            if new_uploads:
                conn.execute("DELETE FROM invitation_uploads WHERE id = ANY(%s)", (list(new_uploads),))
            conn.commit()


def test_a_draft_follows_the_link_and_is_deleted_on_submit(postgres, monkeypatch):
    email = f"pytest-{uuid4().hex}@example.com"
    sent: list[tuple[str, str]] = []

    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)

    def fake_deliver(pairs: list[tuple[str, str]]):
        sent.extend(pairs)
        return list(pairs), []

    monkeypatch.setattr("app.services.campaign_store.deliver_invitations", fake_deliver)
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    headers = {"X-Company-Token": logged.json()["passage"]}
    digest = ""
    with connect() as conn:
        before_answers = _ids(conn, "hse_responses")
        before_invites = _ids(conn, "invitations")
        before_uploads = _ids(conn, "invitation_uploads")
    try:
        uploaded = client.post(
            "/api/v1/company/invitations",
            headers=headers,
            files={"file": ("pytest.csv", f"email\n{email}\n".encode(), "text/csv")},
        )
        assert uploaded.status_code == 200
        token = sent[0][1]
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        opened = client.post("/api/v1/tool/access", json={"token": token})
        assert opened.status_code == 200
        assert opened.json()["draft"] is None
        assert email not in opened.text
        assert token not in opened.text

        partial = [None] * 35
        saved = client.post(
            "/api/v1/tool/drafts",
            json={
                "token": token,
                "place": "profile",
                "index": 4,
                "demographics": {"age_band": "35_44"},
                "answers": partial,
            },
        )
        assert saved.status_code == 200
        with connect() as conn:
            status = conn.execute(
                "SELECT status FROM invitations WHERE email = %s",
                (email,),
            ).fetchone()
            draft = conn.execute(
                """
                SELECT link_token_hash, place, item_index, age_band
                FROM hse_drafts
                WHERE link_token_hash = %s
                """,
                (digest,),
            ).fetchone()
            answer_count = len(_ids(conn, "hse_responses") - before_answers)
        assert status["status"] == "pending"
        assert draft["place"] == "profile"
        assert draft["item_index"] == 0
        assert draft["age_band"] == "35_44"
        assert draft["link_token_hash"] == digest
        assert answer_count == 0

        partial[0] = 4
        again = client.post(
            "/api/v1/tool/drafts",
            json={
                "token": token,
                "place": "ask",
                "index": 2,
                "demographics": {"age_band": "35_44"},
                "answers": partial,
            },
        )
        assert again.status_code == 200
        resumed = client.post("/api/v1/tool/access", json={"token": token})
        assert resumed.status_code == 200
        body = resumed.json()["draft"]
        assert body["place"] == "ask"
        assert body["index"] == 2
        assert body["demographics"] == {"age_band": "35_44"}
        assert body["answers"][0] == 4
        assert body["answers"][1] is None
        assert email not in resumed.text
        assert token not in resumed.text

        refused = client.post(
            "/api/v1/tool/responses",
            json={"token": token, "answers": [3] * 35, "demographics": {"age_band": "35_44"}},
        )
        assert refused.status_code == 400
        with connect() as conn:
            still = conn.execute(
                "SELECT status FROM invitations WHERE link_token_hash = %s",
                (digest,),
            ).fetchone()
            kept = conn.execute(
                "SELECT 1 FROM hse_drafts WHERE link_token_hash = %s",
                (digest,),
            ).fetchone()
        assert still["status"] == "pending"
        assert kept is not None

        finished = client.post(
            "/api/v1/tool/responses",
            json={
                "token": token,
                "answers": [3] * 35,
                "demographics": {"age_band": "35_44", "economic_sector": "health"},
            },
        )
        assert finished.status_code == 200
        assert token not in finished.text
        with connect() as conn:
            gone = conn.execute(
                "SELECT 1 FROM hse_drafts WHERE link_token_hash = %s",
                (digest,),
            ).fetchone()
            stored = conn.execute(
                """
                SELECT demographics
                FROM hse_responses
                WHERE id = ANY(%s)
                """,
                (list(_ids(conn, "hse_responses") - before_answers),),
            ).fetchone()
        assert gone is None
        assert stored["demographics"]["economic_sector"] == "health"
        closed = client.post("/api/v1/tool/access", json={"token": token})
        assert closed.status_code == 409
        late = client.post(
            "/api/v1/tool/drafts",
            json={"token": token, "place": "ask", "index": 0, "demographics": {}, "answers": partial},
        )
        assert late.status_code == 409
    finally:
        with connect() as conn:
            if digest:
                conn.execute("DELETE FROM hse_drafts WHERE link_token_hash = %s", (digest,))
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


def test_a_phone_without_whatsapp_is_not_stored(postgres, monkeypatch):
    monkeypatch.setattr("app.services.campaign_store.whatsapp_ready", lambda settings=None: False)
    _digits, typed, _pretty = _test_phone()
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    response = client.post(
        "/api/v1/company/invitations",
        headers={"X-Company-Token": logged.json()["passage"]},
        files={"file": ("pytest.csv", f"contato\n{typed}\n".encode(), "text/csv")},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "whatsapp_not_configured"
    with connect() as conn:
        found = conn.execute("SELECT 1 FROM invitations WHERE phone = %s", (_digits,)).fetchone()
    assert found is None


def test_a_mixed_list_sends_each_channel_and_keeps_answers_anonymous(postgres, monkeypatch):
    email = f"pytest-{uuid4().hex}@example.com"
    digits, typed, pretty = _test_phone()
    sent_mail: list[tuple[str, str]] = []
    sent_phone: list[tuple[str, str]] = []
    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)
    monkeypatch.setattr("app.services.campaign_store.whatsapp_ready", lambda settings=None: True)

    def fake_mail(pairs):
        sent_mail.extend(pairs)
        return list(pairs), []

    def fake_phone(pairs):
        sent_phone.extend(pairs)
        return list(pairs), []

    monkeypatch.setattr("app.services.campaign_store.deliver_invitations", fake_mail)
    monkeypatch.setattr("app.services.campaign_store.deliver_whatsapp", fake_phone)
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    headers = {"X-Company-Token": logged.json()["passage"]}
    body = f"contato\n{email}\n{typed}\n{pretty}\n".encode()
    with connect() as conn:
        before_invites = _ids(conn, "invitations")
        before_uploads = _ids(conn, "invitation_uploads")
    try:
        response = client.post(
            "/api/v1/company/invitations",
            headers=headers,
            files={"file": ("pytest.csv", body, "text/csv")},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] == 2
        assert payload["duplicates_in_file"] == [pretty]
        assert payload["not_configured"] == []
        assert payload["not_sent"] == []
        assert sent_mail[0][0] == email
        assert sent_phone[0][0] == digits
        assert sent_mail[0][1] not in response.text
        assert sent_phone[0][1] not in response.text
        with connect() as conn:
            mail_row = conn.execute(
                "SELECT channel, phone FROM invitations WHERE email = %s",
                (email,),
            ).fetchone()
            phone_row = conn.execute(
                "SELECT channel, email, link_token FROM invitations WHERE phone = %s",
                (digits,),
            ).fetchone()
        assert mail_row["channel"] == "email"
        assert mail_row["phone"] is None
        assert phone_row["channel"] == "whatsapp"
        assert phone_row["email"] is None
        assert phone_row["link_token"] == sent_phone[0][1]
    finally:
        _drop_new(before_invites, before_uploads)


def test_a_mixed_list_keeps_email_when_whatsapp_is_not_configured(postgres, monkeypatch):
    email = f"pytest-{uuid4().hex}@example.com"
    digits, typed, pretty = _test_phone()
    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)
    monkeypatch.setattr("app.services.campaign_store.whatsapp_ready", lambda settings=None: False)
    monkeypatch.setattr(
        "app.services.campaign_store.deliver_invitations",
        lambda pairs: (list(pairs), []),
    )
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    with connect() as conn:
        before_invites = _ids(conn, "invitations")
        before_uploads = _ids(conn, "invitation_uploads")
    try:
        response = client.post(
            "/api/v1/company/invitations",
            headers={"X-Company-Token": logged.json()["passage"]},
            files={"file": ("pytest.csv", f"email\n{email}\n{typed}\n".encode(), "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["accepted"] == 1
        assert response.json()["not_configured"] == [pretty]
        with connect() as conn:
            kept = conn.execute("SELECT 1 FROM invitations WHERE email = %s", (email,)).fetchone()
            phone = conn.execute("SELECT 1 FROM invitations WHERE phone = %s", (digits,)).fetchone()
        assert kept is not None
        assert phone is None
    finally:
        _drop_new(before_invites, before_uploads)


def test_neither_channel_stores_a_mixed_list(postgres, monkeypatch):
    email = f"pytest-{uuid4().hex}@example.com"
    digits, typed, _pretty = _test_phone()
    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: False)
    monkeypatch.setattr("app.services.campaign_store.whatsapp_ready", lambda settings=None: False)
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    response = client.post(
        "/api/v1/company/invitations",
        headers={"X-Company-Token": logged.json()["passage"]},
        files={"file": ("pytest.csv", f"contato\n{email}\n{typed}\n".encode(), "text/csv")},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "channels_not_configured"
    with connect() as conn:
        mail = conn.execute("SELECT 1 FROM invitations WHERE email = %s", (email,)).fetchone()
        phone = conn.execute("SELECT 1 FROM invitations WHERE phone = %s", (digits,)).fetchone()
    assert mail is None
    assert phone is None


def test_a_refused_whatsapp_keeps_the_phone_when_mail_is_down(postgres, monkeypatch):
    from app.services.campaign_store import dispatch_unsent

    digits, typed, pretty = _test_phone()
    calls: list[list[tuple[str, str]]] = []
    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: False)
    monkeypatch.setattr("app.services.campaign_store.whatsapp_ready", lambda settings=None: True)

    def fake_phone(pairs):
        calls.append(list(pairs))
        if len(calls) == 1:
            return [], [pair[0] for pair in pairs]
        sent = [pair for pair in pairs if pair[0] == digits]
        failed = [pair[0] for pair in pairs if pair[0] != digits]
        return sent, failed

    monkeypatch.setattr("app.services.campaign_store.deliver_whatsapp", fake_phone)
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    headers = {"X-Company-Token": logged.json()["passage"]}
    with connect() as conn:
        before_invites = _ids(conn, "invitations")
        before_uploads = _ids(conn, "invitation_uploads")
    try:
        first = client.post(
            "/api/v1/company/invitations",
            headers=headers,
            files={"file": ("pytest.csv", f"contato\n{typed}\n".encode(), "text/csv")},
        )
        assert first.status_code == 200
        assert first.json()["accepted"] == 0
        assert first.json()["not_sent"] == [pretty]
        roster = client.get("/api/v1/company/invitations", headers=headers)
        assert pretty in roster.json()["unsent"]
        with connect() as conn:
            sent_count = dispatch_unsent(conn)
        assert sent_count == 1
        retried = [pair for pair in calls[1] if pair[0] == digits][0]
        assert retried[1] == calls[0][0][1]
        assert retried[1] not in first.text
        with connect() as conn:
            marked = conn.execute(
                "SELECT sent_at FROM invitations WHERE phone = %s",
                (digits,),
            ).fetchone()
        assert marked["sent_at"] is not None
    finally:
        _drop_new(before_invites, before_uploads)


def _test_phone() -> tuple[str, str, str]:
    national = "119" + f"{uuid4().int % 100_000_000:08d}"
    digits = "55" + national
    typed = f"(11) {national[2:7]}-{national[7:]}"
    pretty = f"+55 11 {national[2:7]}-{national[7:]}"
    return digits, typed, pretty


def _drop_new(before_invites: set, before_uploads: set) -> None:
    with connect() as conn:
        new_invites = _ids(conn, "invitations") - before_invites
        new_uploads = _ids(conn, "invitation_uploads") - before_uploads
        if new_invites:
            conn.execute("DELETE FROM invitations WHERE id = ANY(%s)", (list(new_invites),))
        if new_uploads:
            conn.execute("DELETE FROM invitation_uploads WHERE id = ANY(%s)", (list(new_uploads),))
        conn.commit()


def _ids(conn, table: str) -> set:
    if table not in {"invitations", "invitation_uploads", "hse_responses"}:
        raise AssertionError(table)
    return {row["id"] for row in conn.execute(f"SELECT id FROM {table}").fetchall()}
