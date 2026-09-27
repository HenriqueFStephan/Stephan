"""Create GitHub issues labeled `solve` from the on-site studio overlay."""

from __future__ import annotations

import base64
import binascii
import re
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

import httpx

from app.models.schemas import StudioBlock

GITHUB_API_BASE = "https://api.github.com"
SOLVE_LABEL = "solve"
ALLOWED_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 1_500_000
MAX_IMAGES = 8
MAX_BODY_CHARS = 60_000

RequestFn = Callable[..., tuple[int, Any]]


class GitHubStudioError(Exception):
    """Raised when GitHub rejects a studio request."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Stephan-Studio",
    }


def _default_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.request(method, url, headers=headers, json=json_body)
        if not response.content:
            return response.status_code, None
        try:
            return response.status_code, response.json()
        except ValueError as exc:
            raise GitHubStudioError(f"GitHub returned non-JSON ({response.status_code})") from exc


def decode_image_block(block: StudioBlock) -> tuple[bytes, str, str]:
    """Return (bytes, mime, file extension) for an image block."""
    mime = (block.mime or "image/png").split(";")[0].strip().lower()
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime not in ALLOWED_MIME:
        raise GitHubStudioError(f"Unsupported image type: {mime}", status_code=422)

    raw = block.data_base64
    if raw.startswith("data:"):
        _, _, raw = raw.partition(",")
    raw = "".join(raw.split())
    if not raw:
        raise GitHubStudioError("Image payload is empty", status_code=422)
    try:
        data = base64.b64decode(raw, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise GitHubStudioError("Image payload is not valid base64", status_code=422) from exc
    if not data:
        raise GitHubStudioError("Image payload is empty", status_code=422)
    if len(data) > MAX_IMAGE_BYTES:
        raise GitHubStudioError("Image is too large (max 1.5 MB each)", status_code=422)
    return data, mime, ALLOWED_MIME[mime]


def safe_alt_text(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w.\- ]+", "", name or "").strip()
    return (cleaned or fallback)[:80]


def render_issue_body(blocks: list[StudioBlock], image_urls: dict[str, str]) -> str:
    parts: list[str] = []
    image_index = 0
    for offset, block in enumerate(blocks):
        key = str(offset)
        if block.type == "text":
            text = block.text.strip()
            if text:
                parts.append(text)
                parts.append("")
            continue
        if block.type == "image":
            image_index += 1
            url = image_urls.get(key, "")
            alt = safe_alt_text(block.name, f"snip-{image_index}")
            if url:
                parts.append(f"![{alt}]({url})")
                parts.append("")
    body = "\n".join(parts).strip() + "\n"
    if len(body) > MAX_BODY_CHARS:
        raise GitHubStudioError("Issue body is too large", status_code=422)
    return body


class GitHubStudioClient:
    """Thin GitHub REST helper for studio issues and snip uploads."""

    def __init__(
        self,
        token: str,
        repo: str,
        *,
        branch: str = "studio-attachments",
        api_base: str = GITHUB_API_BASE,
        request: RequestFn | None = None,
    ) -> None:
        self.token = token
        self.repo = repo.strip().strip("/")
        self.branch = branch.strip() or "studio-attachments"
        self.api_base = api_base.rstrip("/")
        self._request = request or (
            lambda method, url, json_body=None: _default_request(
                method, url, headers=github_headers(self.token), json_body=json_body
            )
        )

    def _call(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> tuple[int, Any]:
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        return self._request(method, url, json_body=json_body)

    def _require_ok(self, status: int, payload: Any, action: str, ok: set[int] | None = None) -> Any:
        allowed = ok or {200, 201}
        if status in allowed:
            return payload
        message = ""
        if isinstance(payload, dict):
            message = str(payload.get("message") or "")
        hint = f": {message}" if message else ""
        raise GitHubStudioError(f"GitHub {action} failed ({status}){hint}", status_code=502)

    def ensure_branch(self) -> None:
        status, payload = self._call("GET", f"/repos/{self.repo}/git/ref/heads/{self.branch}")
        if status == 200:
            return
        if status != 404:
            self._require_ok(status, payload, "read branch")

        status, repo_info = self._call("GET", f"/repos/{self.repo}")
        repo_info = self._require_ok(status, repo_info, "read repository")
        default_branch = str(repo_info.get("default_branch") or "main")

        status, default_ref = self._call(
            "GET", f"/repos/{self.repo}/git/ref/heads/{default_branch}"
        )
        default_ref = self._require_ok(status, default_ref, "read default branch")
        sha = ((default_ref.get("object") or {}) if isinstance(default_ref, dict) else {}).get("sha")
        if not sha:
            raise GitHubStudioError("Could not resolve the default branch SHA")

        status, created = self._call(
            "POST",
            f"/repos/{self.repo}/git/refs",
            {"ref": f"refs/heads/{self.branch}", "sha": sha},
        )
        if status in {200, 201, 422}:
            # 422 = ref already exists (race). Treat as success.
            return
        self._require_ok(status, created, "create attachments branch")

    def ensure_solve_label(self) -> None:
        encoded = SOLVE_LABEL
        status, payload = self._call("GET", f"/repos/{self.repo}/labels/{encoded}")
        if status == 200:
            return
        if status != 404:
            self._require_ok(status, payload, "read solve label")
        status, created = self._call(
            "POST",
            f"/repos/{self.repo}/labels",
            {
                "name": SOLVE_LABEL,
                "color": "5319E7",
                "description": "Queue this issue for the AI agent to implement",
            },
        )
        if status in {200, 201, 422}:
            return
        self._require_ok(status, created, "create solve label")

    def upload_image(self, data: bytes, extension: str) -> str:
        self.ensure_branch()
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = f"studio-snips/{day}/{uuid4().hex}{extension}"
        status, payload = self._call(
            "PUT",
            f"/repos/{self.repo}/contents/{path}",
            {
                "message": f"studio snip {path}",
                "content": base64.b64encode(data).decode("ascii"),
                "branch": self.branch,
            },
        )
        payload = self._require_ok(status, payload, "upload snip")
        content = payload.get("content") if isinstance(payload, dict) else None
        download_url = ""
        if isinstance(content, dict):
            download_url = str(content.get("download_url") or "")
        if not download_url:
            download_url = (
                f"https://github.com/{self.repo}/blob/{self.branch}/{path}?raw=true"
            )
        return download_url

    def create_issue(self, title: str, body: str, labels: list[str] | None = None) -> dict[str, Any]:
        payload_body: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload_body["labels"] = labels
        status, payload = self._call(
            "POST",
            f"/repos/{self.repo}/issues",
            payload_body,
        )
        payload = self._require_ok(status, payload, "create issue")
        if not isinstance(payload, dict) or not payload.get("number"):
            raise GitHubStudioError("GitHub did not return an issue number")
        return payload

    def add_solve_label(self, issue_number: int) -> None:
        self.ensure_solve_label()
        status, payload = self._call(
            "POST",
            f"/repos/{self.repo}/issues/{issue_number}/labels",
            {"labels": [SOLVE_LABEL]},
        )
        self._require_ok(status, payload, "label issue", ok={200, 201})

    def publish(self, title: str, blocks: list[StudioBlock]) -> dict[str, Any]:
        image_count = sum(1 for block in blocks if block.type == "image")
        if image_count > MAX_IMAGES:
            raise GitHubStudioError(f"Too many images (max {MAX_IMAGES})", status_code=422)

        image_urls: dict[str, str] = {}
        for offset, block in enumerate(blocks):
            if block.type != "image":
                continue
            data, _mime, extension = decode_image_block(block)
            image_urls[str(offset)] = self.upload_image(data, extension)

        body = render_issue_body(blocks, image_urls)
        self.ensure_solve_label()
        return self.create_issue(title, body, labels=[SOLVE_LABEL])
