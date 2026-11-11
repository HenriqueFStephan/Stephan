"""Account messages. No network."""

from app.core.config import get_settings
from app.services.account_mail import build_confirmation_message, build_reset_message


def test_confirmation_link_lands_on_the_confirm_page(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", "https://stephan.net.br")
    monkeypatch.setenv("SMTP_FROM", "acesso@example.com")
    monkeypatch.setenv("SMTP_USERNAME", "acesso@example.com")
    get_settings.cache_clear()
    message = build_confirmation_message("pessoa@example.com", "token-confirma")
    link = "https://stephan.net.br/confirmar?t=token-confirma"
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()
    assert message["Subject"] == "Stephan — confirme o cadastro"
    assert message["To"] == "pessoa@example.com"
    assert link in plain
    assert f'href="{link}"' in html
    assert "Confirmar o cadastro" in html
    assert "token-confirma" not in message["Subject"]
    get_settings.cache_clear()


def test_reset_link_lands_on_the_password_page(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", "https://stephan.net.br")
    monkeypatch.setenv("SMTP_FROM", "acesso@example.com")
    get_settings.cache_clear()
    message = build_reset_message("pessoa@example.com", "token-senha")
    link = "https://stephan.net.br/senha?t=token-senha"
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()
    assert message["Subject"] == "Stephan — nova senha"
    assert link in plain
    assert f'href="{link}"' in html
    assert "Escolher outra senha" in html
    assert "duas horas" in plain
    get_settings.cache_clear()
