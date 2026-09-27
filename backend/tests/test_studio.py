"""Studio GitHub issue composer and API gate."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.v1 import studio as studio_api
from app.main import app
from app.models.schemas import StudioBlock
from app.services.github_issues import (
    GitHubStudioClient,
    GitHubStudioError,
    decode_image_block,
    render_issue_body,
)

client = TestClient(app)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01"
    b"\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


class FakeSettings:
    def __init__(
        self,
        *,
        github_studio_token: str = "gh-token",
        github_token: str = "",
        github_repo: str = "HenriqueFStephan/Stephan",
        studio_access_token: str = "studio-secret",
        studio_attachments_branch: str = "studio-attachments",
        app_env: str = "development",
    ) -> None:
        self.github_studio_token = github_studio_token
        self.github_token = github_token
        self.github_repo = github_repo
        self.studio_access_token = studio_access_token
        self.studio_attachments_branch = studio_attachments_branch
        self.app_env = app_env

    def resolved_github_token(self) -> str:
        return (self.github_studio_token or self.github_token or "").strip()


def test_render_issue_body_keeps_text_and_images_in_order():
    blocks = [
        StudioBlock(type="text", text="Move the header"),
        StudioBlock(type="image", name="snip 1", data_base64="xx"),
        StudioBlock(type="text", text="Gold accent on CTA"),
    ]
    body = render_issue_body(blocks, {"1": "https://example.com/a.png"})
    assert "Move the header" in body
    assert "![snip 1](https://example.com/a.png)" in body
    assert body.index("Move the header") < body.index("snip 1")
    assert body.index("snip 1") < body.index("Gold accent")
    assert "Filed from the Stephan studio" not in body
    assert "labeled `solve`" not in body


def test_decode_image_rejects_unknown_mime():
    block = StudioBlock(type="image", mime="application/pdf", data_base64=PNG_B64)
    try:
        decode_image_block(block)
        assert False, "expected GitHubStudioError"
    except GitHubStudioError as exc:
        assert exc.status_code == 422


def test_status_reports_missing_tokens(monkeypatch):
    monkeypatch.setattr(
        studio_api,
        "get_settings",
        lambda: FakeSettings(
            github_studio_token="",
            github_token="",
            studio_access_token="",
        ),
    )
    response = client.get("/api/v1/studio/status")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert "GITHUB_STUDIO_TOKEN" in body["missing"]
    assert "STUDIO_ACCESS_TOKEN" in body["missing"]


def test_unlock_rejects_bad_token(monkeypatch):
    monkeypatch.setattr(studio_api, "get_settings", lambda: FakeSettings())
    response = client.post("/api/v1/studio/unlock", headers={"X-Studio-Token": "nope"})
    assert response.status_code == 401


def test_unlock_accepts_matching_token(monkeypatch):
    monkeypatch.setattr(studio_api, "get_settings", lambda: FakeSettings())
    response = client.post(
        "/api/v1/studio/unlock", headers={"X-Studio-Token": "studio-secret"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_create_issue_labels_solve_and_uploads_snips(monkeypatch):
    fake = MagicMock()
    fake.publish.return_value = {
        "number": 77,
        "html_url": "https://github.com/HenriqueFStephan/Stephan/issues/77",
    }
    monkeypatch.setattr(studio_api, "get_settings", lambda: FakeSettings())
    app.dependency_overrides[studio_api.get_github_client] = lambda: fake
    try:
        response = client.post(
            "/api/v1/studio/issues",
            headers={"X-Studio-Token": "studio-secret"},
            json={
                "title": "Shift the gold CTA",
                "blocks": [
                    {"type": "text", "text": "Make the contact button warmer."},
                    {
                        "type": "image",
                        "name": "hero",
                        "mime": "image/png",
                        "data_base64": PNG_B64,
                    },
                ],
            },
        )
    finally:
        app.dependency_overrides.pop(studio_api.get_github_client, None)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["issue_number"] == 77
    assert "77" in body["issue_url"]
    fake.publish.assert_called_once()
    title, blocks = fake.publish.call_args.args
    assert title == "Shift the gold CTA"
    assert blocks[0].type == "text"
    assert blocks[1].type == "image"


def test_create_issue_requires_token(monkeypatch):
    monkeypatch.setattr(studio_api, "get_settings", lambda: FakeSettings())
    response = client.post(
        "/api/v1/studio/issues",
        json={"title": "x", "blocks": [{"type": "text", "text": "hello world"}]},
    )
    assert response.status_code == 401


def test_localhost_skips_studio_token(monkeypatch):
    monkeypatch.setattr(
        studio_api,
        "get_settings",
        lambda: FakeSettings(github_studio_token="", studio_access_token=""),
    )
    local = TestClient(app, base_url="http://127.0.0.1")
    unlock = local.post("/api/v1/studio/unlock")
    assert unlock.status_code == 200
    assert unlock.json()["success"] is True

    issued = local.post(
        "/api/v1/studio/issues",
        json={"title": "Local preview", "blocks": [{"type": "text", "text": "hello world"}]},
    )
    assert issued.status_code == 200
    body = issued.json()
    assert body["success"] is True
    assert body["issue_number"] == 0
    assert "dry-run" in body["message"].lower()


def test_production_localhost_still_requires_token(monkeypatch):
    monkeypatch.setattr(
        studio_api,
        "get_settings",
        lambda: FakeSettings(app_env="production", studio_access_token="studio-secret"),
    )
    local = TestClient(app, base_url="http://127.0.0.1")
    response = local.post("/api/v1/studio/unlock")
    assert response.status_code == 401


def test_github_client_publish_order():
    calls: list[tuple[str, str]] = []

    def fake_request(method: str, url: str, json_body=None):
        calls.append((method, url))
        if url.endswith("/git/ref/heads/studio-attachments"):
            return 200, {"object": {"sha": "abc"}}
        if "/contents/" in url:
            return 201, {"content": {"download_url": "https://raw.example/snip.png"}}
        if url.endswith("/labels/solve") and method == "GET":
            return 200, {"name": "solve"}
        if url.endswith("/issues") and method == "POST":
            assert json_body["title"] == "Fix footer"
            body = json_body["body"]
            assert body.index("hello") < body.index("![hero](https://raw.example/snip.png)")
            assert json_body["labels"] == ["solve"]
            return 201, {"number": 12, "html_url": "https://github.com/org/repo/issues/12"}
        return 500, {"message": f"unexpected {method} {url}"}

    github = GitHubStudioClient("tok", "org/repo", request=fake_request)
    issue = github.publish(
        "Fix footer",
        [
            StudioBlock(type="text", text="hello"),
            StudioBlock(
                type="image",
                name="hero",
                mime="image/png",
                data_base64=PNG_B64,
            ),
        ],
    )
    assert issue["number"] == 12
    assert any(url.endswith("/issues") for _method, url in calls)
    assert any(url.endswith("/labels/solve") for _method, url in calls)
