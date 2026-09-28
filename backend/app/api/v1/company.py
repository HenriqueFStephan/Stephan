"""Company portal. The only account today is the documented demo fixture."""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.models.schemas import CompanyLogin, CompanyLoginResponse, CompanyOverview
from app.services.company_demo import demo_overview

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
