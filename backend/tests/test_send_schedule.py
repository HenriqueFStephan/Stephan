"""The send step: a saved list is held, then the video and the form go out on a schedule."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import connect
from app.main import app
from app.services.campaign_store import VIDEO_LEAD, process_due
from app.services.invitation_mail import build_invitation_message
from app.services.invitation_video import video_link
from app.services.invitation_whatsapp import (
    VIDEO_TEMPLATE_LANG,
    VIDEO_TEMPLATE_NAME,
    build_video_payload,
    deliver_whatsapp,
)


@pytest.fixture(autouse=True)
def _video_is_on_the_server(monkeypatch):
    monkeypatch.setattr("app.services.campaign_store.video_ready", lambda settings=None: True)


class Outbox:
    """Records what the fake channels were asked to send, in order."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def mail(self, pairs, kind="form"):
        for address, _token in pairs:
            self.events.append((kind, address))
        return list(pairs), []

    def of(self, kind: str) -> list[str]:
        return [address for event_kind, address in self.events if event_kind == kind]


@pytest.fixture
def outbox(monkeypatch):
    box = Outbox()
    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)
    monkeypatch.setattr("app.services.campaign_store.deliver_invitations", box.mail)
    return box


@pytest.fixture
def signed_in(postgres):
    client = TestClient(app)
    logged = client.post("/api/v1/company/login", json={"username": "admin", "password": "admintest"})
    headers = {"X-Company-Token": logged.json()["passage"]}
    with connect() as conn:
        internal = conn.execute("SELECT id FROM companies WHERE slug = 'internal'").fetchone()["id"]
        before = {
            table: {row["id"] for row in conn.execute(f"SELECT id FROM {table}").fetchall()}
            for table in ("invitations", "invitation_uploads")
        }
    yield client, headers, internal
    with connect() as conn:
        for table in ("invitations", "invitation_uploads"):
            now = {row["id"] for row in conn.execute(f"SELECT id FROM {table}").fetchall()}
            new = list(now - before[table])
            if not new:
                continue
            if table == "invitations":
                conn.execute("DELETE FROM invitations WHERE id = ANY(%s)", (new,))
            else:
                conn.execute("DELETE FROM form_charges WHERE upload_id = ANY(%s)", (new,))
                conn.execute("DELETE FROM invitation_uploads WHERE id = ANY(%s)", (new,))
        conn.commit()


def _save_list(client, headers, email: str) -> None:
    saved = client.post(
        "/api/v1/company/invitations",
        headers=headers,
        data={"skip": "1"},
        files={"file": ("pytest.csv", f"email\n{email}\n".encode(), "text/csv")},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["accepted"] == 1


def _row(email: str) -> dict:
    with connect() as conn:
        return conn.execute(
            "SELECT video_due_at, video_sent_at, form_due_at, sent_at FROM invitations WHERE email = %s",
            (email,),
        ).fetchone()


def _in(delta: timedelta) -> str:
    return (datetime.now(timezone.utc) + delta).isoformat()


def test_saving_a_list_sends_nothing_and_holds_it(signed_in, outbox):
    client, headers, _internal = signed_in
    email = f"pytest-{uuid4().hex}@example.com"
    _save_list(client, headers, email)
    assert outbox.events == []
    row = _row(email)
    assert row["form_due_at"] is None and row["video_due_at"] is None and row["sent_at"] is None
    roster = client.get("/api/v1/company/invitations", headers=headers).json()
    assert roster["held"] >= 1
    assert email not in roster["unsent"]


def test_a_later_video_and_form_go_out_in_order_and_not_early(signed_in, outbox):
    client, headers, internal = signed_in
    email = f"pytest-{uuid4().hex}@example.com"
    _save_list(client, headers, email)
    video_at = datetime.now(timezone.utc) + timedelta(days=3)
    form_at = video_at + timedelta(days=2)
    released = client.post(
        "/api/v1/company/invitations/send",
        headers=headers,
        json={"mode": "schedule", "video_at": video_at.isoformat(), "form_at": form_at.isoformat()},
    )
    assert released.status_code == 200, released.text
    assert released.json()["immediate"] is False
    roster = client.get("/api/v1/company/invitations", headers=headers).json()
    assert any(item["people"] >= 1 and item["video_at"] and item["form_at"] for item in roster["scheduled"])

    with connect() as conn:
        process_due(conn, company_id=internal, now=video_at - timedelta(minutes=1))
        assert outbox.events == []
        process_due(conn, company_id=internal, now=video_at + timedelta(seconds=5))
        assert outbox.of("video") == [email]
        assert outbox.of("form") == []
        # The form time has not come yet, so a later pass still holds it back.
        process_due(conn, company_id=internal, now=video_at + timedelta(days=1))
        assert outbox.of("form") == []
        process_due(conn, company_id=internal, now=form_at + timedelta(seconds=5))
        assert outbox.of("form") == [email]
        assert outbox.events == [("video", email), ("form", email)]
        # Nothing is sent twice.
        process_due(conn, company_id=internal, now=form_at + timedelta(days=1))
    assert outbox.events == [("video", email), ("form", email)]
    row = _row(email)
    assert row["video_sent_at"] is not None and row["sent_at"] is not None


def test_together_sends_the_video_first_and_the_form_a_moment_later(signed_in, outbox):
    client, headers, internal = signed_in
    email = f"pytest-{uuid4().hex}@example.com"
    _save_list(client, headers, email)
    when = datetime.now(timezone.utc) + timedelta(hours=1)
    released = client.post(
        "/api/v1/company/invitations/send",
        headers=headers,
        json={"mode": "schedule", "video_at": when.isoformat(), "form_at": when.isoformat()},
    )
    assert released.status_code == 200, released.text
    with connect() as conn:
        process_due(conn, company_id=internal, now=when + timedelta(seconds=1))
        assert outbox.events == [("video", email)]
        process_due(conn, company_id=internal, now=when + timedelta(seconds=1) + VIDEO_LEAD + timedelta(seconds=1))
    assert outbox.events == [("video", email), ("form", email)]


def test_a_form_never_goes_before_its_video(signed_in, monkeypatch):
    client, headers, internal = signed_in
    email = f"pytest-{uuid4().hex}@example.com"
    _save_list(client, headers, email)
    seen: list[str] = []

    def refuse_video(pairs, kind="form"):
        seen.append(kind)
        if kind == "video":
            return [], [address for address, _token in pairs]
        return list(pairs), []

    monkeypatch.setattr("app.services.campaign_store.smtp_ready", lambda settings=None: True)
    monkeypatch.setattr("app.services.campaign_store.deliver_invitations", refuse_video)
    released = client.post("/api/v1/company/invitations/send", headers=headers, json={"mode": "now"})
    assert released.status_code == 200, released.text
    later = datetime.now(timezone.utc) + timedelta(hours=2)
    with connect() as conn:
        process_due(conn, company_id=internal, now=later)
        process_due(conn, company_id=internal, now=later + timedelta(minutes=5))
    assert "form" not in seen
    assert _row(email)["sent_at"] is None


def test_now_makes_both_due_immediately(signed_in, outbox):
    client, headers, _internal = signed_in
    email = f"pytest-{uuid4().hex}@example.com"
    _save_list(client, headers, email)
    released = client.post("/api/v1/company/invitations/send", headers=headers, json={"mode": "now"})
    assert released.status_code == 200, released.text
    assert released.json()["immediate"] is True
    assert released.json()["people"] >= 1
    # The response returns first, then the video goes in the background pass.
    assert ("video", email) in outbox.events
    assert ("form", email) not in outbox.events


def test_a_second_send_has_nothing_left_to_release(signed_in, outbox):
    client, headers, _internal = signed_in
    email = f"pytest-{uuid4().hex}@example.com"
    _save_list(client, headers, email)
    assert client.post("/api/v1/company/invitations/send", headers=headers, json={"mode": "now"}).status_code == 200
    again = client.post("/api/v1/company/invitations/send", headers=headers, json={"mode": "now"})
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "nothing_to_send"


def test_the_form_cannot_be_scheduled_before_the_video(signed_in, outbox):
    client, headers, _internal = signed_in
    _save_list(client, headers, f"pytest-{uuid4().hex}@example.com")
    refused = client.post(
        "/api/v1/company/invitations/send",
        headers=headers,
        json={"mode": "schedule", "video_at": _in(timedelta(days=2)), "form_at": _in(timedelta(days=1))},
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "form_before_video"
    far = client.post(
        "/api/v1/company/invitations/send",
        headers=headers,
        json={"mode": "schedule", "video_at": _in(timedelta(days=500)), "form_at": _in(timedelta(days=501))},
    )
    assert far.status_code == 422
    assert far.json()["detail"]["code"] == "too_far"
    naive = client.post(
        "/api/v1/company/invitations/send",
        headers=headers,
        json={"mode": "schedule", "video_at": "2030-01-01T09:00:00", "form_at": "2030-01-02T09:00:00"},
    )
    assert naive.status_code == 422
    assert naive.json()["detail"]["code"] == "bad_schedule"
    with connect() as conn:
        held = conn.execute("SELECT count(*) AS n FROM invitations WHERE form_due_at IS NULL").fetchone()["n"]
    assert held >= 1


def test_sending_is_refused_while_the_video_file_is_missing(signed_in, outbox, monkeypatch):
    client, headers, _internal = signed_in
    email = f"pytest-{uuid4().hex}@example.com"
    _save_list(client, headers, email)
    monkeypatch.setattr("app.services.campaign_store.video_ready", lambda settings=None: False)
    refused = client.post("/api/v1/company/invitations/send", headers=headers, json={"mode": "now"})
    assert refused.status_code == 503
    assert refused.json()["detail"]["code"] == "video_not_configured"
    assert _row(email)["form_due_at"] is None


def test_a_row_sent_before_the_schedule_existed_keeps_a_form_time(postgres):
    with connect() as conn:
        left = conn.execute(
            "SELECT count(*) AS n FROM invitations WHERE sent_at IS NOT NULL AND form_due_at IS NULL"
        ).fetchone()["n"]
    assert left == 0


def test_the_video_is_served_only_to_a_holder_of_a_link(signed_in, outbox, tmp_path, monkeypatch):
    client, headers, _internal = signed_in
    clip = tmp_path / "tutorial.mp4"
    clip.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"x" * 64)
    monkeypatch.setenv("TUTORIAL_VIDEO_PATH", str(clip))
    get_settings.cache_clear()
    try:
        email = f"pytest-{uuid4().hex}@example.com"
        _save_list(client, headers, email)
        with connect() as conn:
            token = conn.execute("SELECT link_token FROM invitations WHERE email = %s", (email,)).fetchone()["link_token"]
        served = client.get("/api/v1/video", params={"t": token})
        assert served.status_code == 200
        assert served.headers["content-type"] == "video/mp4"
        assert served.content.startswith(b"\x00\x00\x00\x18ftyp")
        partial = client.get("/api/v1/video", params={"t": token}, headers={"Range": "bytes=0-7"})
        assert partial.status_code == 206
        assert len(partial.content) == 8
        assert client.get("/api/v1/video", params={"t": "x" * 43}).status_code == 404
        assert client.get("/api/v1/video").status_code == 422
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert digest not in served.text
        monkeypatch.setenv("TUTORIAL_VIDEO_PATH", str(tmp_path / "missing.mp4"))
        get_settings.cache_clear()
        assert client.get("/api/v1/video", params={"t": token}).status_code == 404
    finally:
        get_settings.cache_clear()


def test_the_whatsapp_video_carries_the_video_as_its_header():
    link = "https://stephan.net.br/api/v1/video?t=abc"
    body = build_video_payload("5511987654321", link)
    assert body["to"] == "5511987654321"
    assert body["template"]["name"] == VIDEO_TEMPLATE_NAME == "stephan_video_forca_e_luz"
    assert body["template"]["language"]["code"] == VIDEO_TEMPLATE_LANG == "pt_BR"
    assert body["template"]["components"] == [
        {"type": "header", "parameters": [{"type": "video", "video": {"link": link}}]}
    ]


def test_deliver_whatsapp_posts_the_video_template_with_the_per_person_link(monkeypatch):
    captured: dict = {}

    class Response:
        status_code = 200

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return Response()

    monkeypatch.setenv("WHATSAPP_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "12345")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.invitation_whatsapp.httpx.post", fake_post)
    try:
        sent, failed = deliver_whatsapp([("5511987654321", "tok-1")], kind="video")
        settings = get_settings()
    finally:
        get_settings.cache_clear()
    assert failed == [] and sent == [("5511987654321", "tok-1")]
    header = captured["json"]["template"]["components"][0]
    assert header["type"] == "header"
    assert header["parameters"][0]["video"]["link"] == video_link("tok-1", settings)
    assert "tok-1" in header["parameters"][0]["video"]["link"]
    assert "test-token" not in str(captured["json"])


def test_the_video_email_links_to_the_video_and_not_the_form():
    settings = get_settings()
    message = build_invitation_message("pessoa@example.com", "tok-1", settings, kind="video")
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()
    assert "/api/v1/video?t=tok-1" in plain
    assert "/api/v1/video?t=tok-1" in html
    assert "/tool?t=" not in plain and "/tool?t=" not in html
    assert "Assistir ao vídeo" in html
    assert "vídeo" in message["Subject"]
    form = build_invitation_message("pessoa@example.com", "tok-1", settings)
    assert "/tool?t=tok-1" in form.get_body(preferencelist=("plain",)).get_content()
    assert "Abrir o questionário" in form.get_body(preferencelist=("html",)).get_content()
