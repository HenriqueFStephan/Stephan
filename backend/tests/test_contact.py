"""Contact form stores a message and rejects a bad address."""

from fastapi.testclient import TestClient

from app.core.config import DATA_DIR
from app.main import app

client = TestClient(app)


def test_contact_appends_a_message():
    path = DATA_DIR / "messages.jsonl"
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    response = client.post(
        "/api/v1/contact",
        json={
            "name": "Ana",
            "organization": "Oficina",
            "email": "ana@example.com",
            "message": "Quero conversar sobre o trabalho.",
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    after = path.read_text(encoding="utf-8")
    assert "ana@example.com" in after
    assert after.startswith(before)


def test_contact_rejects_a_bad_email():
    response = client.post(
        "/api/v1/contact",
        json={
            "name": "Ana",
            "email": "not-an-email",
            "message": "Olá",
        },
    )
    assert response.status_code == 422
