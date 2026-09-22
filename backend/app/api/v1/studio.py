"""On-site studio API — unlock gate and GitHub `solve` issue creation."""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.config import get_settings
from app.models.schemas import (
    StudioIssueCreate,
    StudioIssueResponse,
    StudioStatusResponse,
    StudioUnlockResponse,
)
from app.services.github_issues import GitHubStudioClient, GitHubStudioError

router = APIRouter(prefix="/studio", tags=["studio"])

TOKEN_HEADER = "X-Studio-Token"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
LOCAL_DRY_RUN_MESSAGE = (
    "Local dry-run: GitHub token is not set, so no issue was opened."
)


def studio_missing_config() -> list[str]:
    settings = get_settings()
    missing: list[str] = []
    if not settings.resolved_github_token():
        missing.append("GITHUB_STUDIO_TOKEN")
    if not (settings.github_repo or "").strip():
        missing.append("GITHUB_REPO")
    if not (settings.studio_access_token or "").strip():
        missing.append("STUDIO_ACCESS_TOKEN")
    return missing


def is_local_request(request: Request) -> bool:
    """Skip studio secrets on loopback hosts outside production."""
    settings = get_settings()
    if (settings.app_env or "").strip().lower() == "production":
        return False
    host = (request.url.hostname or "").lower().strip("[]")
    return host in LOCAL_HOSTS


def tokens_match(provided: str, expected: str) -> bool:
    left = hashlib.sha256(provided.encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


def require_studio_token(
    request: Request,
    x_studio_token: Annotated[str | None, Header(alias=TOKEN_HEADER)] = None,
) -> str:
    if is_local_request(request):
        return (x_studio_token or "").strip() or "local"
    settings = get_settings()
    expected = (settings.studio_access_token or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Studio is not configured")
    provided = (x_studio_token or "").strip()
    if not provided or not tokens_match(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid studio token")
    return provided


def get_github_client(request: Request) -> GitHubStudioClient | None:
    settings = get_settings()
    token = settings.resolved_github_token()
    repo = (settings.github_repo or "").strip()
    if not token or not repo:
        if is_local_request(request):
            return None
        raise HTTPException(status_code=503, detail="Studio is not configured")
    return GitHubStudioClient(
        token,
        repo,
        branch=settings.studio_attachments_branch or "studio-attachments",
    )


@router.get("/status", response_model=StudioStatusResponse)
def studio_status() -> StudioStatusResponse:
    missing = studio_missing_config()
    return StudioStatusResponse(configured=not missing, missing=missing)


@router.post("/unlock", response_model=StudioUnlockResponse)
def studio_unlock(_token: str = Depends(require_studio_token)) -> StudioUnlockResponse:
    return StudioUnlockResponse(success=True, message="Studio unlocked")


@router.post("/issues", response_model=StudioIssueResponse)
def create_studio_issue(
    payload: StudioIssueCreate,
    _token: str = Depends(require_studio_token),
    client: GitHubStudioClient | None = Depends(get_github_client),
) -> StudioIssueResponse:
    has_content = any(
        (block.type == "text" and block.text.strip())
        or (block.type == "image" and block.data_base64.strip())
        for block in payload.blocks
    )
    if not has_content:
        raise HTTPException(status_code=422, detail="Issue body is empty")

    if client is None:
        return StudioIssueResponse(
            success=True,
            issue_url="",
            issue_number=0,
            message=LOCAL_DRY_RUN_MESSAGE,
        )

    try:
        issue = client.publish(payload.title, payload.blocks)
    except GitHubStudioError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    number = int(issue.get("number") or 0)
    url = str(issue.get("html_url") or "")
    return StudioIssueResponse(
        success=True,
        issue_url=url,
        issue_number=number,
        message=f"Opened issue #{number}",
    )
