"""Company portal. The only account today is the documented demo fixture.

Invitation lists for the pilot company are stored in PostgreSQL. The simulated
overview is unchanged.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.db.session import DatabaseUnavailable, connect, ensure_schema
from app.models.schemas import (
    CompanyLogin,
    CompanyLoginResponse,
    CompanyOverview,
    InvitationRoster,
    InvitationUploadResult,
)
from app.services.campaign_store import NoOpenRound, add_invitations, list_invitations
from app.services.company_demo import demo_overview
from app.services.invitation_file import InvitationFileError, parse_invitation_file
from app.services.invitation_mail import MailDeliveryError, MailNotConfigured

router = APIRouter(prefix="/company", tags=["company"])

TOKEN_HEADER = "X-Company-Token"

# Published test account. See docs/COMPANY_PORTAL.md. Not for real employee data.
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "admintest"
PASSAGE_LABEL = b"stephan-company-v1"


def secrets_match(provided: str, expected: str) -> bool:
    left = hashlib.sha256(provided.encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


def passage_for(username: str) -> str:
    """Session clearance. Not the password, and not reversible to it."""
    return hmac.new(DEMO_PASSWORD.encode("utf-8"), PASSAGE_LABEL + username.encode("utf-8"), hashlib.sha256).hexdigest()


def require_company_token(
    x_company_token: Annotated[str | None, Header(alias=TOKEN_HEADER)] = None,
) -> str:
    provided = (x_company_token or "").strip()
    if not provided or not secrets_match(provided, passage_for(DEMO_USERNAME)):
        raise HTTPException(status_code=401, detail="Invalid company session")
    return provided


@router.post("/login", response_model=CompanyLoginResponse)
def company_login(body: CompanyLogin) -> CompanyLoginResponse:
    username_ok = secrets_match(body.username, DEMO_USERNAME)
    password_ok = secrets_match(body.password, DEMO_PASSWORD)
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return CompanyLoginResponse(success=True, passage=passage_for(DEMO_USERNAME))


@router.get("/overview", response_model=CompanyOverview)
def company_overview(_token: str = Depends(require_company_token)) -> CompanyOverview:
    return CompanyOverview.model_validate(demo_overview())


@router.get("/invitations", response_model=InvitationRoster)
def company_invitations(_token: str = Depends(require_company_token)) -> InvitationRoster:
    try:
        with connect() as conn:
            ensure_schema(conn)
            roster = list_invitations(conn)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except NoOpenRound as exc:
        raise HTTPException(status_code=409, detail={"code": "no_open_round"}) from exc
    return InvitationRoster.model_validate(roster)


@router.post("/invitations", response_model=InvitationUploadResult)
def upload_company_invitations(
    file: UploadFile = File(...),
    _token: str = Depends(require_company_token),
) -> InvitationUploadResult:
    data = file.file.read(1_000_001)
    if len(data) > 1_000_000:
        raise HTTPException(status_code=400, detail={"code": "bad_file"})
    try:
        parsed = parse_invitation_file(file.filename or "", data)
    except InvitationFileError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "columns": exc.columns},
        ) from exc
    try:
        with connect() as conn:
            ensure_schema(conn)
            stored = add_invitations(conn, file.filename or "", parsed)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except NoOpenRound as exc:
        raise HTTPException(status_code=409, detail={"code": "no_open_round"}) from exc
    except MailNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_not_configured"}) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=502, detail={"code": "mail_failed"}) from exc
    return InvitationUploadResult.model_validate(stored)
