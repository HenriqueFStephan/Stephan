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


def test_contact_notice_carries_the_message(monkeypatch):
    notices: list[tuple[str, str]] = []

    def capture(subject: str, body: str) -> bool:
        notices.append((subject, body))
        return True

    monkeypatch.setattr("app.api.v1.contact.notify_consulting", capture)
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
    assert notices[0][0] == "Stephan — mensagem de contato"
    assert "Quero conversar sobre o trabalho." in notices[0][1]
    assert "ana@example.com" in notices[0][1]


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
