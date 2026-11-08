"""WhatsApp invitation payload. No call leaves the test."""

from __future__ import annotations

import json

import pytest

from app.core.config import get_settings
from app.services.invitation_whatsapp import (
    TEMPLATE_LANG,
    TEMPLATE_NAME,
    WhatsAppNotConfigured,
    deliver_whatsapp,
)


def test_the_template_carries_the_link_and_not_the_token(monkeypatch):
    captured: dict = {}

    class Response:
        status_code = 200

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("WHATSAPP_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "12345")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.invitation_whatsapp.httpx.post", fake_post)
    try:
        sent, failed = deliver_whatsapp([("5519998772525", "link-token")])
    finally:
        get_settings.cache_clear()

    assert failed == []
    assert sent == [("5519998772525", "link-token")]
    assert captured["url"] == "https://graph.facebook.com/v26.0/12345/messages"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["timeout"] == 30
    body = captured["json"]
    assert body["messaging_product"] == "whatsapp"
    assert body["to"] == "5519998772525"
    assert body["type"] == "template"
    assert body["template"]["name"] == TEMPLATE_NAME
    assert body["template"]["language"]["code"] == TEMPLATE_LANG
    link = body["template"]["components"][0]["parameters"][0]["text"]
    assert link.endswith("/tool?t=link-token")
    assert "test-token" not in json.dumps(body)


def test_a_rejected_token_stops_the_rest_of_the_batch(monkeypatch):
    codes = [200, 401]

    class Response:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    def fake_post(url, headers, json, timeout):
        return Response(codes.pop(0))

    monkeypatch.setenv("WHATSAPP_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "12345")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.invitation_whatsapp.httpx.post", fake_post)
    try:
        sent, failed = deliver_whatsapp(
            [("5511999990001", "one"), ("5511999990002", "two"), ("5511999990003", "three")]
        )
    finally:
        get_settings.cache_clear()

    assert [phone for phone, _token in sent] == ["5511999990001"]
    assert failed == ["5511999990002", "5511999990003"]
    assert codes == []


def test_missing_whatsapp_settings_refuse_the_send(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(WhatsAppNotConfigured):
            deliver_whatsapp([("5519998772525", "link-token")])
    finally:
        get_settings.cache_clear()
