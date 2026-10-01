"""Invitation messages. No network."""

from app.core.config import get_settings
from app.services.invitation_mail import build_invitation_message, smtp_ready


def test_message_is_only_the_link(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:4200")
    monkeypatch.setenv("SMTP_FROM", "lista@example.com")
    monkeypatch.setenv("SMTP_USERNAME", "lista@example.com")
    get_settings.cache_clear()
    message = build_invitation_message("pessoa@example.com", "token-1")
    link = "http://localhost:4200/tool?t=token-1"
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()
    assert message["To"] == "pessoa@example.com"
    assert message["From"] == "lista@example.com"
    assert message["Subject"] == "Stephan — link para o questionário"
    assert link in plain
    assert f'href="{link}"' in html
    assert "#0f3f62" in html
    assert "cid:stephan-lockup" in html
    assert "Abrir o questionário" in html
    assert "pessoa@example.com" not in plain
    assert "pessoa@example.com" not in html
    image = message.get_body(preferencelist=("related",)).get_payload()[1]
    assert image.get_content_type() == "image/png"
    assert image["Content-ID"] == "<stephan-lockup>"
    assert image["Content-Disposition"] == "inline"
    get_settings.cache_clear()


def test_smtp_is_not_ready_without_a_password(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "lista@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    get_settings.cache_clear()
    assert smtp_ready() is False
    get_settings.cache_clear()
