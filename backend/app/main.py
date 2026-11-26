"""
Stephan FastAPI application entry point.

Run: uvicorn app.main:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.v1 import cnpj, company, contact, orders, studio, tool, video
from app.core.config import get_settings
from app.core.cors import configure_cors
from app.db.session import DatabaseUnavailable, connect, ensure_schema
from app.models.schemas import HealthResponse

settings = get_settings()
log = logging.getLogger(__name__)

# How often the server looks for a video or a form whose time has come.
SEND_PASS_SECONDS = 60


def _send_pass() -> None:
    """One pass: send what is due. A database that is down is tried again next time."""
    try:
        with connect() as conn:
            ensure_schema(conn)
            from app.services.campaign_store import dispatch_unsent

            dispatch_unsent(conn)
    except DatabaseUnavailable:
        pass
    except Exception as exc:  # one bad pass must not stop the next one
        log.warning("send pass failed: %s", type(exc).__name__)


async def _send_loop() -> None:
    while True:
        await asyncio.to_thread(_send_pass)
        await asyncio.sleep(SEND_PASS_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """On the server, send each video and form when its scheduled time comes."""
    task = None
    if get_settings().app_env == "production":
        task = asyncio.create_task(_send_loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="Stephan API",
    description="Stephan — psychosocial risk assessment and management.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

configure_cors(app)

API_PREFIX = "/api/v1"

app.include_router(contact.router, prefix=API_PREFIX)
app.include_router(orders.router, prefix=API_PREFIX)
app.include_router(cnpj.router, prefix=API_PREFIX)
app.include_router(studio.router, prefix=API_PREFIX)
app.include_router(company.router, prefix=API_PREFIX)
app.include_router(tool.router, prefix=API_PREFIX)
app.include_router(video.router, prefix=API_PREFIX)


def _health() -> HealthResponse:
    current = get_settings()
    password = (current.smtp_password or "").replace(" ", "")
    github_ok = bool(current.resolved_github_token() and current.github_repo)
    studio_ok = bool(github_ok and (current.studio_access_token or "").strip())
    return HealthResponse(
        status="ok",
        environment=current.app_env,
        smtp_configured=bool(current.smtp_host and password),
        studio_configured=studio_ok,
        whatsapp_configured=bool(
            (current.whatsapp_token or "").strip() and (current.whatsapp_phone_number_id or "").strip()
        ),
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Render health check. Not proxied by Netlify."""
    return _health()


@app.get(f"{API_PREFIX}/status", response_model=HealthResponse, tags=["health"])
def api_status() -> HealthResponse:
    """Same payload as /health, under /api/v1 so the Netlify proxy can reach it."""
    return _health()


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "name": "Stephan API",
        "docs": "/docs",
        "status": f"{API_PREFIX}/status",
    }
