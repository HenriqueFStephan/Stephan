"""Company portal. Each login is one company. Lists and answers stay inside it.

Statistics are that company's own round. Invitation lists are stored in PostgreSQL.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile

from app.db.session import DatabaseUnavailable, connect, ensure_schema
from app.models.schemas import (
    CompanyLogin,
    CompanyLoginResponse,
    CompanyOverview,
    CompanyRoundRow,
    InvitationRoster,
    InvitationUploadResult,
)
from app.services.campaign_store import NoOpenRound, add_invitations, list_invitations, list_rounds
from app.services.company_accounts import (
    CompanySession,
    authenticate,
    issue_passage,
    session_from_passage,
)
from app.services.company_overview import overview_for_round
from app.services.invitation_file import InvitationFileError, parse_invitation_file
from app.services.invitation_mail import MailDeliveryError, MailNotConfigured

router = APIRouter(prefix="/company", tags=["company"])

TOKEN_HEADER = "X-Company-Token"


def require_company_token(
    x_company_token: Annotated[str | None, Header(alias=TOKEN_HEADER)] = None,
) -> CompanySession:
    provided = (x_company_token or "").strip()
    if not provided:
        raise HTTPException(status_code=401, detail="Invalid company session")
    try:
        with connect() as conn:
            ensure_schema(conn)
            session = session_from_passage(conn, provided)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid company session")
    return session


@router.post("/login", response_model=CompanyLoginResponse)
def company_login(body: CompanyLogin) -> CompanyLoginResponse:
    try:
        with connect() as conn:
            ensure_schema(conn)
            session = authenticate(conn, body.username, body.password)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return CompanyLoginResponse(
        success=True,
        passage=issue_passage(session),
        company_slug=session.slug,
        company_name=session.name,
    )


@router.get("/overview", response_model=CompanyOverview)
def company_overview(
    round_label: Annotated[str, Query(alias="round", min_length=1, max_length=120)],
    session: CompanySession = Depends(require_company_token),
) -> CompanyOverview:
    """Aggregate for one round of the signed-in company. Another company's round is absent."""
    try:
        with connect() as conn:
            ensure_schema(conn)
            overview = overview_for_round(conn, session.company_id, session.slug, round_label.strip())
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    if overview is None:
        raise HTTPException(status_code=404, detail={"code": "unknown_round"})
    return CompanyOverview.model_validate(overview)


@router.get("/invitations", response_model=InvitationRoster)
def company_invitations(session: CompanySession = Depends(require_company_token)) -> InvitationRoster:
    try:
        with connect() as conn:
            ensure_schema(conn)
            roster = list_invitations(conn, session.company_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except NoOpenRound as exc:
        raise HTTPException(status_code=409, detail={"code": "no_open_round"}) from exc
    return InvitationRoster.model_validate(roster)


@router.get("/rounds", response_model=list[CompanyRoundRow])
def company_rounds(session: CompanySession = Depends(require_company_token)) -> list[CompanyRoundRow]:
    try:
        with connect() as conn:
            ensure_schema(conn)
            rows = list_rounds(conn, session.company_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    return [CompanyRoundRow.model_validate(row) for row in rows]


@router.post("/invitations", response_model=InvitationUploadResult)
def upload_company_invitations(
    file: UploadFile = File(...),
    session: CompanySession = Depends(require_company_token),
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
            stored = add_invitations(conn, session.company_id, file.filename or "", parsed)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except NoOpenRound as exc:
        raise HTTPException(status_code=409, detail={"code": "no_open_round"}) from exc
    except MailNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_not_configured"}) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=502, detail={"code": "mail_failed"}) from exc
    return InvitationUploadResult.model_validate(stored)
