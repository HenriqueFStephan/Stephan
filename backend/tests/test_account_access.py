"""Confirmation and password reset. The two seeded accounts are already open."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import connect
from app.main import app
from app.services.invitation_mail import MailNotConfigured
from tests.test_orders import payload

client = TestClient(app)


def test_seeded_accounts_are_confirmed(postgres):
    with connect() as conn:
        rows = {
            row["username"]: row
            for row in conn.execute(
                """
                SELECT username, email, confirmed_at
                FROM company_users
                WHERE username IN ('admin', 'artigo')
                """
            ).fetchall()
        }
    assert rows["admin"]["email"] == "henrique.f.stephan@gmail.com"
    assert rows["artigo"]["email"] == "celsostephan@gmail.com"
    assert rows["admin"]["confirmed_at"] is not None
    assert rows["artigo"]["confirmed_at"] is not None

    admin = client.post(
        "/api/v1/company/login",
        json={"username": "henrique.f.stephan@gmail.com", "password": "admintest"},
    )
    assert admin.status_code == 200
    assert admin.json()["company_slug"] == "internal"

    artigo = client.post(
        "/api/v1/company/login",
        json={"username": "celsostephan@gmail.com", "password": "voltarassamambanhas"},
    )
    assert artigo.status_code == 200
    assert artigo.json()["company_slug"] == "hse-it"


def test_forgot_password_reaches_the_seeded_email_and_replaces_a_confirmed_password(postgres, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr("app.api.v1.company.send_reset", lambda address, token: sent.append((address, token)))

    quiet = client.post("/api/v1/company/password/forgot", json={"email": "nobody@example.com"})
    assert quiet.status_code == 200
    assert sent == []

    asked = client.post("/api/v1/company/password/forgot", json={"email": "admin"})
    assert asked.status_code == 200
    assert sent[0][0] == "henrique.f.stephan@gmail.com"
    still = client.post(
        "/api/v1/company/login",
        json={"username": "admin", "password": "admintest"},
    )
    assert still.status_code == 200

    email = f"reset-{uuid4().hex[:8]}@example.com"
    digits = "00000082000174"
    confirms: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.api.v1.orders.send_confirmation",
        lambda address, token: confirms.append((address, token)),
    )
    try:
        created = client.post(
            "/api/v1/orders",
            json=payload(access_email=email, password="senha-segura", cnpj="00.000.082/0001-74"),
        )
        assert created.status_code == 200
        opened = client.post("/api/v1/company/confirm", json={"token": confirms[0][1]})
        assert opened.status_code == 200
        before = len(sent)
        asked_again = client.post("/api/v1/company/password/forgot", json={"email": email})
        assert asked_again.status_code == 200
        token = sent[before][1]
        changed = client.post(
            "/api/v1/company/password/reset",
            json={"token": token, "password": "senha-nova-123"},
        )
        assert changed.status_code == 200
        used = client.post(
            "/api/v1/company/password/reset",
            json={"token": token, "password": "senha-nova-123"},
        )
        assert used.status_code == 400
        old = client.post(
            "/api/v1/company/login",
            json={"username": email, "password": "senha-segura"},
        )
        assert old.status_code == 401
        new = client.post(
            "/api/v1/company/login",
            json={"username": email, "password": "senha-nova-123"},
        )
        assert new.status_code == 200
    finally:
        _drop(email, digits)


def test_an_unconfirmed_signup_can_ask_for_another_link(postgres, monkeypatch):
    email = f"again-{uuid4().hex[:8]}@example.com"
    digits = "00000081000120"
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr("app.api.v1.orders.send_confirmation", lambda address, token: sent.append((address, token)))
    monkeypatch.setattr("app.api.v1.company.send_confirmation", lambda address, token: sent.append((address, token)))
    resets: list[tuple[str, str]] = []
    monkeypatch.setattr("app.api.v1.company.send_reset", lambda address, token: resets.append((address, token)))
    try:
        created = client.post(
            "/api/v1/orders",
            json=payload(access_email=email, password="senha-segura", cnpj="00.000.081/0001-20"),
        )
        assert created.status_code == 200
        first = sent[0][1]

        forgot = client.post("/api/v1/company/password/forgot", json={"email": email})
        assert forgot.status_code == 200
        assert resets == []

        resent = client.post("/api/v1/company/confirm/resend", json={"email": email})
        assert resent.status_code == 200
        assert sent[1][0] == email.casefold()
        stale = client.post("/api/v1/company/confirm", json={"token": first})
        assert stale.status_code == 400
        opened = client.post("/api/v1/company/confirm", json={"token": sent[1][1]})
        assert opened.status_code == 200
    finally:
        _drop(email, digits)


def test_an_expired_confirmation_link_does_not_open_the_account(postgres, monkeypatch):
    email = f"late-{uuid4().hex[:8]}@example.com"
    digits = "11222333000181"
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr("app.api.v1.orders.send_confirmation", lambda address, token: sent.append((address, token)))
    try:
        created = client.post(
            "/api/v1/orders",
            json=payload(access_email=email, password="senha-segura", cnpj="11.222.333/0001-81"),
        )
        assert created.status_code == 200
        with connect() as conn:
            conn.execute(
                """
                UPDATE company_users
                SET confirm_expires_at = %s
                WHERE email = %s
                """,
                (datetime.now(timezone.utc) - timedelta(hours=1), email.casefold()),
            )
        refused = client.post("/api/v1/company/confirm", json={"token": sent[0][1]})
        assert refused.status_code == 400
        login = client.post(
            "/api/v1/company/login",
            json={"username": email, "password": "senha-segura"},
        )
        assert login.status_code == 403
    finally:
        _drop(email, digits)


def test_signup_is_rolled_back_when_the_confirmation_cannot_be_sent(postgres, monkeypatch):
    email = f"nomail-{uuid4().hex[:8]}@example.com"
    digits = "00000080000185"

    def refuse(address, token):
        raise MailNotConfigured()

    monkeypatch.setattr("app.api.v1.orders.send_confirmation", refuse)
    try:
        response = client.post(
            "/api/v1/orders",
            json=payload(access_email=email, password="senha-segura", cnpj="00.000.080/0001-85"),
        )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "mail_not_configured"
        with connect() as conn:
            found = conn.execute(
                "SELECT 1 FROM companies WHERE cnpj = %s",
                (digits,),
            ).fetchone()
        assert found is None
    finally:
        _drop(email, digits)


def _drop(email: str, digits: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            DELETE FROM company_users
            WHERE email = %s
               OR company_id IN (SELECT id FROM companies WHERE cnpj = %s)
            """,
            (email.casefold(), digits),
        )
        conn.execute("DELETE FROM companies WHERE cnpj = %s", (digits,))
