"""Signup opens the first access email for a company. Further emails are more rows.

The row stays closed until the confirmation link is opened.
"""

import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import DATA_DIR
from app.db.session import connect
from app.main import app
from tests.test_orders import payload

client = TestClient(app)


def test_signup_stays_closed_until_the_email_is_confirmed(postgres, monkeypatch):
    email = f"signup-{uuid4().hex[:8]}@example.com"
    cnpj = "00.000.080/0001-85"
    digits = "00000080000185"
    password = "senha-segura"
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr("app.api.v1.orders.send_confirmation", lambda address, token: sent.append((address, token)))
    try:
        response = client.post(
            "/api/v1/orders",
            json=payload(access_email=email, password=password, cnpj=cnpj),
        )
        assert response.status_code == 200
        stored = json.loads((DATA_DIR / "orders.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        assert stored["access_email"] == email
        assert "password" not in stored
        assert password not in json.dumps(stored)
        assert sent[0][0] == email.casefold()
        assert sent[0][1] 

        closed = client.post(
            "/api/v1/company/login",
            json={"username": email, "password": password},
        )
        assert closed.status_code == 403
        assert closed.json()["detail"]["code"] == "email_unconfirmed"

        wrong = client.post(
            "/api/v1/company/login",
            json={"username": email, "password": "outra-senha"},
        )
        assert wrong.status_code == 401

        confirmed = client.post("/api/v1/company/confirm", json={"token": sent[0][1]})
        assert confirmed.status_code == 200
        again = client.post("/api/v1/company/confirm", json={"token": sent[0][1]})
        assert again.status_code == 400

        login = client.post(
            "/api/v1/company/login",
            json={"username": email, "password": password},
        )
        assert login.status_code == 200
        assert login.json()["success"] is True

        again = client.post(
            "/api/v1/orders",
            json=payload(access_email=email, password=password, cnpj="00.000.081/0001-20"),
        )
        assert again.status_code == 409
        assert again.json()["detail"]["code"] == "email_taken"

        same_company = client.post(
            "/api/v1/orders",
            json=payload(access_email=f"outro-{uuid4().hex[:8]}@example.com", password=password, cnpj=cnpj),
        )
        assert same_company.status_code == 409
        assert same_company.json()["detail"]["code"] == "cnpj_taken"

        with connect() as conn:
            row = conn.execute(
                """
                SELECT u.role, u.email, c.cnpj
                FROM company_users AS u
                JOIN companies AS c ON c.id = u.company_id
                WHERE u.email = %s
                """,
                (email,),
            ).fetchone()
        assert row["role"] == "owner"
        assert row["email"] == email
        assert row["cnpj"] == digits
    finally:
        with connect() as conn:
            conn.execute("DELETE FROM company_users WHERE email = %s OR company_id IN (SELECT id FROM companies WHERE cnpj = %s)", (email, digits))
            conn.execute("DELETE FROM companies WHERE cnpj = %s", (digits,))
