"""
Stephan FastAPI application entry point.

Run: uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI

from app.api.v1 import contact, studio
from app.core.config import get_settings
from app.core.cors import configure_cors
from app.models.schemas import HealthResponse

settings = get_settings()

app = FastAPI(
    title="Stephan API",
    description="Stephan — psychosocial risk assessment and management.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

configure_cors(app)

API_PREFIX = "/api/v1"

app.include_router(contact.router, prefix=API_PREFIX)
app.include_router(studio.router, prefix=API_PREFIX)


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
