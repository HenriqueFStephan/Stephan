"""Send one invitation link per new address.

The message carries the link and nothing else about the person. Tokens are not
logged. If the SMTP settings are missing, nothing is stored as invited.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings, get_settings

log = logging.getLogger(__name__)

_LOCKUP = Path(__file__).resolve().parents[1] / "assets" / "brand" / "stephan-lockup.png"
_LOCKUP_CID = "stephan-lockup"


class MailNotConfigured(Exception):
    """SMTP host, username, or password is missing."""


class MailDeliveryError(Exception):
    """The server rejected the login or the connection."""


def smtp_ready(settings: Settings | None = None) -> bool:
    current = settings or get_settings()
    password = _password(current)
    return bool(current.smtp_host and current.smtp_username and password)


def invitation_link(token: str, settings: Settings | None = None) -> str:
    current = settings or get_settings()
    origin = (current.public_app_url or "https://stephan.net.br").rstrip("/")
    return f"{origin}/tool?t={token}"


def build_invitation_message(recipient: str, token: str, settings: Settings | None = None) -> EmailMessage:
    current = settings or get_settings()
    sender = (current.smtp_from or current.smtp_username).strip()
    link = invitation_link(token, current)
    message = EmailMessage()
    message["Subject"] = "Stephan — link para o questionário"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(_plain(link))
    message.add_alternative(_html(link), subtype="html")
    lockup = _lockup_bytes()
    if lockup:
        html_part = message.get_payload()[-1]
        html_part.add_related(lockup, maintype="image", subtype="png", cid=f"<{_LOCKUP_CID}>")
        image = html_part.get_payload()[-1]
        image.replace_header("Content-Disposition", "inline")
    return message


def deliver_invitations(pairs: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[str]]:
    """Send each (email, token). Return the pairs that left, and the addresses that did not."""
    if not pairs:
        return [], []
    current = get_settings()
    if not smtp_ready(current):
        raise MailNotConfigured()
    try:
        smtp = smtplib.SMTP(current.smtp_host, current.smtp_port, timeout=30)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(current.smtp_username, _password(current))
    except Exception as exc:
        log.warning("invitation mail could not sign in: %s", type(exc).__name__)
        raise MailDeliveryError() from exc
    sent: list[tuple[str, str]] = []
    failed: list[str] = []
    try:
        for recipient, token in pairs:
            try:
                smtp.send_message(build_invitation_message(recipient, token, current))
            except Exception as exc:
                log.warning("invitation mail was refused: %s", type(exc).__name__)
                failed.append(recipient)
                continue
            sent.append((recipient, token))
    finally:
        try:
            smtp.quit()
        except Exception:
            pass
    return sent, failed


def _password(settings: Settings) -> str:
    return (settings.smtp_password or "").replace(" ", "")


def _plain(link: str) -> str:
    return (
        "stephan\n\n"
        "Questionário das condições de trabalho\n\n"
        "Este é o seu link para o questionário das condições de trabalho.\n\n"
        f"{link}\n\n"
        "O link é só seu. Não o reencaminhe.\n"
    )


def _html(link: str) -> str:
    mark = ""
    if _lockup_bytes():
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
  <div style="display:none;max-height:0;overflow:hidden;">Este é o seu link para o questionário das condições de trabalho.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f7f4ec;">
    <tr>
      <td align="center" style="padding:48px 24px;">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="width:480px;max-width:480px;">
          <tr>
            <td style="padding:0;font-family:'Source Sans 3',Helvetica,Arial,sans-serif;color:#1c2b33;text-align:left;">
              {mark}
              <h1 style="margin:0 0 12px;font-family:Outfit,'Source Sans 3',Helvetica,Arial,sans-serif;font-size:28px;line-height:1.15;font-weight:500;letter-spacing:-0.03em;color:#0f3f62;">Questionário das condições de trabalho</h1>
              <p style="margin:0 0 28px;font-size:18px;line-height:1.5;color:#1c2b33;">Este é o seu link para o questionário das condições de trabalho.</p>
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td bgcolor="#0f3f62" style="border-radius:999px;background:#0f3f62;">
                    <a href="{link}" style="display:inline-block;padding:14px 22px;font-family:'Source Sans 3',Helvetica,Arial,sans-serif;font-size:16px;line-height:1;color:#f7f4ec;text-decoration:none;border-radius:999px;">Abrir o questionário</a>
                  </td>
                </tr>
              </table>
              <p style="margin:28px 0 0;font-size:15px;line-height:1.5;color:#5c6b73;">O link é só seu. Não o reencaminhe.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


@lru_cache(maxsize=1)
def _lockup_bytes() -> bytes:
    try:
        return _LOCKUP.read_bytes()
    except OSError:
        log.warning("invitation lockup is missing")
        return b""
