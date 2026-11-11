"""Confirmation and password-reset messages.

The link is the only secret in the body. Tokens are not logged.
"""

from __future__ import annotations

from email.message import EmailMessage

from app.core.config import Settings, get_settings
from app.services.invitation_mail import (
    _LOCKUP_CID,
    attach_lockup,
    deliver_one,
    lockup_available,
)


def confirmation_link(token: str, settings: Settings | None = None) -> str:
    return f"{_origin(settings)}/confirmar?t={token}"


def reset_link(token: str, settings: Settings | None = None) -> str:
    return f"{_origin(settings)}/senha?t={token}"


def build_confirmation_message(recipient: str, token: str, settings: Settings | None = None) -> EmailMessage:
    link = confirmation_link(token, settings)
    return _message(
        recipient,
        "Stephan — confirme o cadastro",
        "Abra o link para ativar o acesso da empresa. Ele vale por 48 horas.",
        "Confirme o cadastro",
        "Abra o link para ativar o acesso da empresa. Ele vale por 48 horas.",
        "Se você não fez este cadastro, ignore esta mensagem.",
        "Confirmar o cadastro",
        link,
        settings,
    )


def build_reset_message(recipient: str, token: str, settings: Settings | None = None) -> EmailMessage:
    link = reset_link(token, settings)
    return _message(
        recipient,
        "Stephan — nova senha",
        "Abra o link para escolher outra senha. Ele vale por duas horas.",
        "Nova senha",
        "Abra o link para escolher outra senha. Ele vale por duas horas.",
        "Se você não pediu esta troca, ignore esta mensagem.",
        "Escolher outra senha",
        link,
        settings,
    )


def send_confirmation(recipient: str, token: str) -> None:
    deliver_one(build_confirmation_message(recipient, token))


def send_reset(recipient: str, token: str) -> None:
    deliver_one(build_reset_message(recipient, token))


def _origin(settings: Settings | None) -> str:
    current = settings or get_settings()
    return (current.public_app_url or "https://stephan.net.br").rstrip("/")


def _message(
    recipient: str,
    subject: str,
    preview: str,
    title: str,
    lead: str,
    note: str,
    button: str,
    link: str,
    settings: Settings | None,
) -> EmailMessage:
    current = settings or get_settings()
    sender = (current.smtp_from or current.smtp_username).strip()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(f"stephan\n\n{title}\n\n{lead}\n\n{link}\n\n{note}\n")
    message.add_alternative(_html(preview, title, lead, note, button, link), subtype="html")
    attach_lockup(message)
    return message


def _html(preview: str, title: str, lead: str, note: str, button: str, link: str) -> str:
    mark = ""
    if lockup_available():
        mark = (
            f'<img src="cid:{_LOCKUP_CID}" width="104" alt="Stephan" '
            'style="display:block;width:104px;height:auto;border:0;margin:0 0 28px;">'
        )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f7f4ec;">
  <div style="display:none;max-height:0;overflow:hidden;">{preview}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f7f4ec;">
    <tr>
      <td align="center" style="padding:48px 24px;">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="width:480px;max-width:480px;">
          <tr>
            <td style="padding:0;font-family:'Source Sans 3',Helvetica,Arial,sans-serif;color:#1c2b33;text-align:left;">
              {mark}
              <h1 style="margin:0 0 12px;font-family:Outfit,'Source Sans 3',Helvetica,Arial,sans-serif;font-size:28px;line-height:1.15;font-weight:500;letter-spacing:-0.03em;color:#0f3f62;">{title}</h1>
              <p style="margin:0 0 28px;font-size:18px;line-height:1.5;color:#1c2b33;">{lead}</p>
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td bgcolor="#0f3f62" style="border-radius:999px;background:#0f3f62;">
                    <a href="{link}" style="display:inline-block;padding:14px 22px;font-family:'Source Sans 3',Helvetica,Arial,sans-serif;font-size:16px;line-height:1;color:#f7f4ec;text-decoration:none;border-radius:999px;">{button}</a>
                  </td>
                </tr>
              </table>
              <p style="margin:28px 0 0;font-size:15px;line-height:1.5;color:#5c6b73;">{note}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
