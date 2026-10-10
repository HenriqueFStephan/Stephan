"""Orders store a company signup and never a card number."""

import json

from fastapi.testclient import TestClient

from app.core.config import DATA_DIR
from app.main import app

client = TestClient(app)


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
        "rep_name": "Ana Lima",
        "rep_cpf": "529.982.247-25",
        "rep_role": "Diretora",
        "rep_email": "ana@oficina.example",
        "rep_phone": "(11) 98888-7777",
        "contact_name": "Ana Lima",
        "contact_role": "Diretora",
        "contact_email": "ana@oficina.example",
        "contact_phone": "(11) 98888-7777",
        "accept_contract": True,
        "privacy_ack": True,
        "marketing": False,
        "method": "pix",
        "installments": 1,
        "summary_ack": True,
        "quoted_price_cents": None,
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
    assert "52998224725" in stored["rep_cpf"].replace(".", "").replace("-", "")


def test_order_rejects_a_bad_cnpj_and_a_missing_acceptance():
    bad_cnpj = client.post("/api/v1/orders", json=payload(cnpj="11.111.111/1111-11"))
    assert bad_cnpj.status_code == 422
    declined = client.post("/api/v1/orders", json=payload(accept_contract=False))
    assert declined.status_code == 422


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
