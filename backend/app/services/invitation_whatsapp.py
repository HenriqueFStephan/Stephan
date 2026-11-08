"""Send one invitation link per phone on WhatsApp.

The business number is +55 19 99877-2525. Meta's Cloud API sends a template,
because the company starts the conversation. The template name is
stephan_questionario, language pt_BR, and {{1}} is the full link. The wording
to approve is in docs/MANUAL_STEPS.md. Tokens are not logged.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import Settings, get_settings
from app.services.invitation_mail import invitation_link

log = logging.getLogger(__name__)

GRAPH_VERSION = "v26.0"
TEMPLATE_NAME = "stephan_questionario"
TEMPLATE_LANG = "pt_BR"


class WhatsAppNotConfigured(Exception):
    """The Cloud API token or the phone number id is missing."""


class WhatsAppDeliveryError(Exception):
    """Meta rejected the token. Further numbers in this batch will not be tried."""


class ChannelsNotConfigured(Exception):
    """The file needs email and WhatsApp, and neither channel is ready."""


def whatsapp_ready(settings: Settings | None = None) -> bool:
    current = settings or get_settings()
    return bool((current.whatsapp_token or "").strip() and (current.whatsapp_phone_number_id or "").strip())


def build_payload(phone: str, link: str) -> dict:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": link}],
                }
            ],
        },
    }


def deliver_whatsapp(pairs: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[str]]:
    """Send each (phone, token). Return the pairs that were accepted, and the numbers that were not."""
    if not pairs:
        return [], []
    current = get_settings()
    if not whatsapp_ready(current):
        raise WhatsAppNotConfigured()
    sent: list[tuple[str, str]] = []
    failed: list[str] = []
    abort = False
    for phone, token in pairs:
        if abort:
            failed.append(phone)
            continue
        try:
            _post(current, phone, invitation_link(token, current))
        except WhatsAppDeliveryError:
            log.warning("whatsapp invitation was refused: auth")
            abort = True
            failed.append(phone)
            continue
        except Exception as exc:
            log.warning("whatsapp invitation was refused: %s", type(exc).__name__)
            failed.append(phone)
            continue
        sent.append((phone, token))
    return sent, failed


def _post(settings: Settings, phone: str, link: str) -> None:
    number_id = settings.whatsapp_phone_number_id.strip()
    response = httpx.post(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{number_id}/messages",
        headers={"Authorization": f"Bearer {settings.whatsapp_token.strip()}"},
        json=build_payload(phone, link),
        timeout=30,
    )
    if response.status_code in (401, 403):
        raise WhatsAppDeliveryError()
    if response.status_code >= 400:
        raise RuntimeError(str(response.status_code))
