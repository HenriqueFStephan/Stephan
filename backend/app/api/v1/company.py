"""Company portal. Each login is one company. Lists and answers stay inside it.

Statistics are that company's own round. Invitation lists are stored in PostgreSQL.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile

from app.db.session import DatabaseUnavailable, connect, ensure_schema
from app.models.schemas import (
    AccountAck,
    AccountEmail,
    AccountToken,
    ChargeMethodChoice,
    CompanyLogin,
    CompanyLoginResponse,
    CompanyOverview,
    CompanyRoundRow,
    FormQuote,
    InvitationRetryResult,
    ListQuote,
    InvitationRoster,
    InvitationUploadResult,
    PasswordReset,
)
from app.services.campaign_store import (
    ChargeNotFound,
    NoOpenRound,
    add_invitations,
    choose_form_charge,
    list_invitations,
    preview_invitations,
    list_rounds,
    retry_unsent,
)
from app.services.form_pricing import (
    PaymentRequired,
    SkipNotAllowed,
    UnknownPaymentMethod,
    gate_payment,
)
from app.services.account_mail import send_confirmation, send_reset
from app.services.company_accounts import (
    CompanySession,
    EmailUnconfirmed,
    apply_password_reset,
    authenticate,
    begin_password_reset,
    confirm_access,
    issue_passage,
    reissue_confirmation,
    session_from_passage,
)
from app.services.company_overview import overview_for_round
from app.services.invitation_file import InvitationFileError, parse_invitation_file
from app.services.invitation_mail import MailDeliveryError, MailNotConfigured
from app.services.invitation_whatsapp import (
    ChannelsNotConfigured,
    WhatsAppDeliveryError,
    WhatsAppNotConfigured,
)

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
    except EmailUnconfirmed as exc:
        raise HTTPException(status_code=403, detail={"code": "email_unconfirmed"}) from exc
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return CompanyLoginResponse(
        success=True,
        passage=issue_passage(session),
        company_slug=session.slug,
        company_name=session.name,
    )


@router.post("/confirm", response_model=AccountAck)
def confirm_company_email(body: AccountToken) -> AccountAck:
    """Open the account named by the confirmation link. The link is single use."""
    try:
        with connect() as conn:
            ensure_schema(conn)
            opened = confirm_access(conn, body.token)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    if not opened:
        raise HTTPException(status_code=400, detail={"code": "invalid_token"})
    return AccountAck()


@router.post("/confirm/resend", response_model=AccountAck)
def resend_company_confirmation(body: AccountEmail) -> AccountAck:
    """Send another confirmation when the account is still closed. A missing email stays quiet."""
    try:
        with connect() as conn:
            ensure_schema(conn)
            pending = reissue_confirmation(conn, body.email)
            if pending is not None:
                send_confirmation(*pending)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except MailNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_not_configured"}) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_failed"}) from exc
    return AccountAck()


@router.post("/password/forgot", response_model=AccountAck)
def forgot_company_password(body: AccountEmail) -> AccountAck:
    """Send a reset link to a confirmed email. An unknown address gets the same answer."""
    try:
        with connect() as conn:
            ensure_schema(conn)
            pending = begin_password_reset(conn, body.email)
            if pending is not None:
                send_reset(*pending)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except MailNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_not_configured"}) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_failed"}) from exc
    return AccountAck()


@router.post("/password/reset", response_model=AccountAck)
def reset_company_password(body: PasswordReset) -> AccountAck:
    """Store a new password when the reset link is still valid."""
    try:
        with connect() as conn:
            ensure_schema(conn)
            changed = apply_password_reset(conn, body.token, body.password)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    if not changed:
        raise HTTPException(status_code=400, detail={"code": "invalid_token"})
    return AccountAck()


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


def _parsed_upload(file: UploadFile):
    data = file.file.read(1_000_001)
    if len(data) > 1_000_000:
        raise HTTPException(status_code=400, detail={"code": "bad_file"})
    try:
        return parse_invitation_file(file.filename or "", data)
    except InvitationFileError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "columns": exc.columns},
        ) from exc


@router.post("/invitations/quote", response_model=ListQuote)
def quote_company_invitations(
    file: UploadFile = File(...),
    session: CompanySession = Depends(require_company_token),
) -> ListQuote:
    """Price the file. The addresses stay unstored and no message goes out."""
    parsed = _parsed_upload(file)
    try:
        with connect() as conn:
            ensure_schema(conn)
            preview = preview_invitations(conn, session.company_id, parsed)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except NoOpenRound as exc:
        raise HTTPException(status_code=409, detail={"code": "no_open_round"}) from exc
    return ListQuote.model_validate(preview)


@router.post("/invitations", response_model=InvitationUploadResult)
def upload_company_invitations(
    file: UploadFile = File(...),
    method: Annotated[str, Form()] = "",
    skip: Annotated[str, Form()] = "",
    session: CompanySession = Depends(require_company_token),
) -> InvitationUploadResult:
    parsed = _parsed_upload(file)
    release = skip.strip().lower() in {"1", "true", "yes"}
    if release and session.slug != "internal":
        raise HTTPException(status_code=403, detail={"code": "skip_not_allowed"})
    try:
        with connect() as conn:
            ensure_schema(conn)
            preview = preview_invitations(conn, session.company_id, parsed)
            try:
                chosen = gate_payment(session.slug, method, release, preview["forms"])
            except PaymentRequired as exc:
                raise HTTPException(status_code=409, detail={"code": "payment_required"}) from exc
            except SkipNotAllowed as exc:
                raise HTTPException(status_code=403, detail={"code": "skip_not_allowed"}) from exc
            except UnknownPaymentMethod as exc:
                raise HTTPException(status_code=422, detail={"code": "unknown_method"}) from exc
            stored = add_invitations(
                conn,
                session.company_id,
                file.filename or "",
                parsed,
                method=chosen,
                skipped=release,
            )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except NoOpenRound as exc:
        raise HTTPException(status_code=409, detail={"code": "no_open_round"}) from exc
    except MailNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_not_configured"}) from exc
    except WhatsAppNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "whatsapp_not_configured"}) from exc
    except ChannelsNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "channels_not_configured"}) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=502, detail={"code": "mail_failed"}) from exc
    except WhatsAppDeliveryError as exc:
        raise HTTPException(status_code=502, detail={"code": "whatsapp_failed"}) from exc
    return InvitationUploadResult.model_validate(stored)


@router.post("/charges/{charge_id}", response_model=FormQuote)
def choose_company_charge(
    charge_id: str,
    payload: ChargeMethodChoice,
    session: CompanySession = Depends(require_company_token),
) -> FormQuote:
    """Store the chosen method for this list. Does not debit."""
    try:
        UUID(charge_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "charge_not_found"}) from exc
    try:
        with connect() as conn:
            ensure_schema(conn)
            quote = choose_form_charge(conn, session.company_id, charge_id, payload.method)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except UnknownPaymentMethod as exc:
        raise HTTPException(status_code=422, detail={"code": "unknown_method"}) from exc
    except ChargeNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "charge_not_found"}) from exc
    return FormQuote.model_validate(quote)


@router.post("/invitations/retry", response_model=InvitationRetryResult)
def retry_company_invitations(
    session: CompanySession = Depends(require_company_token),
) -> InvitationRetryResult:
    """Send the stored link again for addresses in this round whose message never left."""
    try:
        with connect() as conn:
            ensure_schema(conn)
            result = retry_unsent(conn, session.company_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except NoOpenRound as exc:
        raise HTTPException(status_code=409, detail={"code": "no_open_round"}) from exc
    except MailNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "mail_not_configured"}) from exc
    except WhatsAppNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "whatsapp_not_configured"}) from exc
    except ChannelsNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "channels_not_configured"}) from exc
    return InvitationRetryResult.model_validate(result)
