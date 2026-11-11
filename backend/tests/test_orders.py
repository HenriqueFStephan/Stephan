"""Orders store a company signup and never a card number."""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import DATA_DIR
from app.main import app

client = TestClient(app)


class _QuietConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture(autouse=True)
def skip_account(monkeypatch):
    """Order tests record the file. Account rows are covered in test_signup_access."""
    monkeypatch.setattr("app.api.v1.orders.connect", lambda: _QuietConnection())
    monkeypatch.setattr("app.api.v1.orders.ensure_schema", lambda conn: None)
    monkeypatch.setattr(
        "app.api.v1.orders.provision_company_access",
        lambda *args, **kwargs: ("ana@oficina.example", "token"),
    )
    monkeypatch.setattr("app.api.v1.orders.send_confirmation", lambda *args, **kwargs: None)


def payload(**overrides):
    body = {
        "legal_name": "Oficina Ltda",
        "trade_name": "",
        "cnpj": "11.222.333/0001-81",
        "municipal_registration": "",
        "nfe_email": "fiscal@oficina.example",
        "phone": "(11) 3333-4444",
        "postal_code": "01310-100",
        "street": "Avenida Paulista",
        "number": "1000",
        "complement": "",
        "district": "Bela Vista",
        "city": "São Paulo",
        "state": "sp",
        "headcount": 40,
        "sites": 1,
        "activity": "Metalurgia",
        "access_email": "ana@oficina.example",
        "password": "senha-segura",
        "accept_contract": True,
        "privacy_ack": True,
        "marketing": False,
        "method": "pix",
        "installments": 1,
        "summary_ack": True,
        "plan": "hse",
        "quoted_price_cents": 69_000,
    }
    body.update(overrides)
    return body


def test_order_is_stored_and_not_charged():
    path = DATA_DIR / "orders.jsonl"
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    response = client.post("/api/v1/orders", json=payload())
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["charged"] is False
    assert len(body["reference"]) == 10
    after = path.read_text(encoding="utf-8")
    assert after.startswith(before)
    stored = json.loads(after.splitlines()[-1])
    assert stored["reference"] == body["reference"]
    assert stored["charged"] is False
    assert stored["state"] == "SP"
    assert stored["marketing"] is False
    assert stored["plan"] == "hse"
    assert stored["quoted_price_cents"] == 69_000
    assert stored["access_email"] == "ana@oficina.example"
    assert "password" not in stored
    assert "senha-segura" not in json.dumps(stored)


def test_order_notice_names_the_company_and_skips_the_cpf(monkeypatch):
    notices: list[tuple[str, str]] = []

    def capture(subject: str, body: str) -> bool:
        notices.append((subject, body))
        return True

    monkeypatch.setattr("app.api.v1.orders.notify_consulting", capture)
    response = client.post("/api/v1/orders", json=payload())
    assert response.status_code == 200
    assert "Oficina Ltda" in notices[0][1]
    assert response.json()["reference"] in notices[0][1]
    assert "senha-segura" not in notices[0][1]
    assert "ana@oficina.example" in notices[0][1]


def test_order_uses_the_access_email_when_the_invoice_email_is_blank():
    response = client.post("/api/v1/orders", json=payload(nfe_email="", phone=""))
    assert response.status_code == 200
    path = DATA_DIR / "orders.jsonl"
    stored = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert stored["nfe_email"] == "ana@oficina.example"
    assert stored["phone"] == ""


def test_order_rejects_a_short_password():
    short = client.post("/api/v1/orders", json=payload(password="curta"))
    assert short.status_code == 422


def test_order_rejects_a_bad_cnpj():
    bad_cnpj = client.post("/api/v1/orders", json=payload(cnpj="11.111.111/1111-11"))
    assert bad_cnpj.status_code == 422


def test_order_stores_signup_without_a_chosen_plan(monkeypatch):
    notices: list[tuple[str, str]] = []

    def capture(subject: str, body: str) -> bool:
        notices.append((subject, body))
        return True

    monkeypatch.setattr("app.api.v1.orders.notify_consulting", capture)
    body = payload()
    for key in ("accept_contract", "privacy_ack", "summary_ack", "method", "plan", "quoted_price_cents"):
        body.pop(key)
    response = client.post("/api/v1/orders", json=body)
    assert response.status_code == 200
    assert response.json()["charged"] is False
    path = DATA_DIR / "orders.jsonl"
    stored = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert stored["plan"] is None
    assert stored["method"] is None
    assert stored["quoted_price_cents"] is None
    assert stored["accept_contract"] is False
    assert "Plano:" not in notices[0][1]


def test_order_rejects_a_quote_outside_the_band():
    mismatch = client.post("/api/v1/orders", json=payload(quoted_price_cents=1))
    assert mismatch.status_code == 422
    unknown = client.post("/api/v1/orders", json=payload(plan="ciclo"))
    assert unknown.status_code == 422


def test_order_stores_the_larger_plan_on_its_band():
    response = client.post(
        "/api/v1/orders",
        json=payload(plan="analise", headcount=220, quoted_price_cents=469_000),
    )
    assert response.status_code == 200
    path = DATA_DIR / "orders.jsonl"
    stored = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert stored["plan"] == "analise"
    assert stored["headcount"] == 220
    assert stored["quoted_price_cents"] == 469_000
    assert stored["charged"] is False


def test_order_drops_a_card_number():
    path = DATA_DIR / "orders.jsonl"
    response = client.post(
        "/api/v1/orders",
        json=payload(card_number="4111111111111111", cvv="123"),
    )
    assert response.status_code == 200
    last = path.read_text(encoding="utf-8").splitlines()[-1]
    assert "4111111111111111" not in last
    assert "card_number" not in last
    assert "cvv" not in last
