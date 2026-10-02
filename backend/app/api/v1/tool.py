"""Campaign form. A link token opens one anonymous response for that invitation's company.

The token is the lookup key. The answer row does not store it, the address, or the invitation id.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db.session import DatabaseUnavailable, connect, ensure_schema
from app.models.schemas import (
    ToolAccessRequest,
    ToolAccessResponse,
    ToolDraft,
    ToolDraftRequest,
    ToolSubmitRequest,
    ToolSubmitResponse,
)
from app.services.campaign_store import (
    DemographicRejected,
    InvitationAlreadySubmitted,
    UnknownInvitation,
    open_pending_invitation,
    save_draft,
    submit_invitation,
)

router = APIRouter(prefix="/tool", tags=["tool"])


@router.post("/access", response_model=ToolAccessResponse)
def tool_access(body: ToolAccessRequest) -> ToolAccessResponse:
    try:
        with connect() as conn:
            ensure_schema(conn)
            draft = open_pending_invitation(conn, body.token)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except UnknownInvitation as exc:
        raise HTTPException(status_code=404, detail={"code": "unknown_link"}) from exc
    except InvitationAlreadySubmitted as exc:
        raise HTTPException(status_code=409, detail={"code": "link_used"}) from exc
    return ToolAccessResponse(state="ready", draft=ToolDraft.model_validate(draft) if draft else None)


@router.post("/drafts", response_model=ToolSubmitResponse)
def tool_draft(body: ToolDraftRequest) -> ToolSubmitResponse:
    try:
        with connect() as conn:
            ensure_schema(conn)
            save_draft(
                conn,
                body.token,
                place=body.place,
                item_index=body.index,
                demographics=body.demographics,
                answers=body.answers,
            )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except UnknownInvitation as exc:
        raise HTTPException(status_code=404, detail={"code": "unknown_link"}) from exc
    except InvitationAlreadySubmitted as exc:
        raise HTTPException(status_code=409, detail={"code": "link_used"}) from exc
    except DemographicRejected as exc:
        raise HTTPException(status_code=400, detail={"code": "demographics"}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "answers"}) from exc
    return ToolSubmitResponse(saved=True)


@router.post("/responses", response_model=ToolSubmitResponse)
def tool_response(body: ToolSubmitRequest) -> ToolSubmitResponse:
    submitted_on = datetime.now(timezone.utc).date()
    try:
        with connect() as conn:
            ensure_schema(conn)
            submit_invitation(
                conn,
                body.token,
                submitted_on=submitted_on,
                demographics=body.demographics,
                answers=body.answers,
            )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except UnknownInvitation as exc:
        raise HTTPException(status_code=404, detail={"code": "unknown_link"}) from exc
    except InvitationAlreadySubmitted as exc:
        raise HTTPException(status_code=409, detail={"code": "link_used"}) from exc
    except DemographicRejected as exc:
        raise HTTPException(status_code=400, detail={"code": "demographics"}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "answers"}) from exc
    return ToolSubmitResponse(saved=True)
