"""CORS middleware configuration."""

import os

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings


# Intended production origin. Update this once Netlify assigns the real site URL.
LIVE_FRONTEND_ORIGINS = ("https://stephan-psico.netlify.app",)


def configure_cors(app) -> None:
    """Attach CORS middleware allowing the configured frontend origin(s)."""
    settings = get_settings()
    origins = [
        settings.frontend_url,
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        *LIVE_FRONTEND_ORIGINS,
    ]

    extra = os.getenv("CORS_EXTRA_ORIGINS", "")
    if extra:
        origins.extend(o.strip() for o in extra.split(",") if o.strip())

    seen: set[str] = set()
    unique_origins = []
    for origin in origins:
        if origin not in seen:
            seen.add(origin)
            unique_origins.append(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=unique_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
