"""The internal account can place a list and send it for another company.

The rows are that company's. The internal company does not keep a copy.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import connect
from app.main import app


def _quiet(monkeypatch):
    monkeypatch.setattr("app.services.campaign_store.video_ready", lambda settings=None: True)
    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)
    monkeypatch.setattr(
        "app.services.campaign_store.deliver_invitations",
        lambda pairs, kind="form": (list(pairs), []),
    )


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    logged = client.post("/api/v1/company/login", json={"username": username, "password": password})
    assert logged.status_code == 200, logged.text
    return {"X-Company-Token": logged.json()["passage"]}


def test_only_the_internal_account_sees_every_company(postgres):
    client = TestClient(app)
    admin = _login(client, "admin", "admintest")
    listed = client.get("/api/v1/company/accounts", headers=admin)
    assert listed.status_code == 200
    by_slug = {row["slug"]: row for row in listed.json()}
    assert by_slug["internal"]["username"] == "admin"
    assert by_slug["internal"]["name"] == "Uso interno"
    assert by_slug["hse-it"]["username"] == "artigo"
    assert "held" in by_slug["hse-it"]

    artigo = _login(client, "artigo", "voltarassamambanhas")
    refused = client.get("/api/v1/company/accounts", headers=artigo)
    assert refused.status_code == 403
    assert refused.json()["detail"]["code"] == "not_admin"


def test_placing_and_sending_for_a_company_writes_that_companys_rows(postgres, monkeypatch):
    _quiet(monkeypatch)
    client = TestClient(app)
    admin = _login(client, "admin", "admintest")
    artigo = _login(client, "artigo", "voltarassamambanhas")
    email = f"pytest-{uuid4().hex}@example.com"
    slug = f"pytest-{uuid4().hex[:12]}"
    company_id = uuid4()
    with connect() as conn:
        conn.execute(
            "INSERT INTO companies (id, slug, name) VALUES (%s, %s, %s)",
            (company_id, slug, "Pytest Ltda"),
        )
        conn.commit()
    try:
        missing = client.post(
            "/api/v1/company/accounts/nao-existe/invitations",
            headers=admin,
            data={"method": "pix"},
            files={"file": ("lista.csv", f"email\n{email}\n".encode(), "text/csv")},
        )
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "company_not_found"

        skipped = client.post(
            f"/api/v1/company/accounts/{slug}/invitations",
            headers=admin,
            data={"skip": "1"},
            files={"file": ("lista.csv", f"email\n{email}\n".encode(), "text/csv")},
        )
        assert skipped.status_code == 403
        assert skipped.json()["detail"]["code"] == "skip_not_allowed"

        saved = client.post(
            f"/api/v1/company/accounts/{slug}/invitations",
            headers=admin,
            data={"method": "pix"},
            files={"file": ("lista.csv", f"email\n{email}\n".encode(), "text/csv")},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["accepted"] == 1
        assert saved.json()["quote"]["method"] == "pix"

        with connect() as conn:
            row = conn.execute(
                """
                SELECT c.slug, i.form_due_at, f.method, f.status
                FROM invitations AS i
                JOIN companies AS c ON c.id = i.company_id
                JOIN form_charges AS f ON f.upload_id = i.upload_id
                WHERE i.email = %s
                """,
                (email,),
            ).fetchone()
            on_internal = conn.execute(
                """
                SELECT 1
                FROM invitations AS i
                JOIN companies AS c ON c.id = i.company_id
                WHERE i.email = %s
                  AND c.slug = 'internal'
                """,
                (email,),
            ).fetchone()
        assert row["slug"] == slug
        assert row["form_due_at"] is None
        assert row["method"] == "pix"
        assert row["status"] == "method_chosen"
        assert on_internal is None

        sent = client.post(
            f"/api/v1/company/accounts/{slug}/invitations/send",
            headers=admin,
            json={"mode": "now"},
        )
        assert sent.status_code == 200, sent.text
        assert sent.json()["people"] == 1
        assert sent.json()["immediate"] is True

        with connect() as conn:
            after = conn.execute(
                """
                SELECT c.slug, i.video_due_at, i.form_due_at
                FROM invitations AS i
                JOIN companies AS c ON c.id = i.company_id
                WHERE i.email = %s
                """,
                (email,),
            ).fetchone()
        assert after["slug"] == slug
        assert after["video_due_at"] is not None
        assert after["form_due_at"] is not None

        refused = client.post(
            f"/api/v1/company/accounts/{slug}/invitations/send",
            headers=artigo,
            json={"mode": "now"},
        )
        assert refused.status_code == 403
    finally:
        with connect() as conn:
            conn.execute("DELETE FROM invitations WHERE company_id = %s", (company_id,))
            conn.execute("DELETE FROM form_charges WHERE company_id = %s", (company_id,))
            conn.execute("DELETE FROM invitation_uploads WHERE company_id = %s", (company_id,))
            conn.execute("DELETE FROM company_rounds WHERE company_id = %s", (company_id,))
            conn.execute("DELETE FROM companies WHERE id = %s", (company_id,))
            conn.commit()
