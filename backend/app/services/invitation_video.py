"""The tutorial video that goes out before the form.

The file is one mp4 on the server. It is served only at /api/v1/video?t=<token>,
and the token is the invitation's own link token, so a person can open it with
the message they received and nobody else can. WhatsApp sends it as the header
of the template stephan_video_forca_e_luz (pt_BR). An email carries the same link.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, get_settings

DEFAULT_VIDEO = Path(__file__).resolve().parents[1] / "assets" / "video" / "tutorial.mp4"


def video_file(settings: Settings | None = None) -> Path | None:
    """The mp4 to serve, or None when it has not been placed on the server."""
    current = settings or get_settings()
    configured = (current.tutorial_video_path or "").strip()
    path = Path(configured) if configured else DEFAULT_VIDEO
    return path if path.is_file() else None


def video_ready(settings: Settings | None = None) -> bool:
    return video_file(settings) is not None


def video_link(token: str, settings: Settings | None = None) -> str:
    current = settings or get_settings()
    origin = (current.public_app_url or "https://stephan.net.br").rstrip("/")
    return f"{origin}/api/v1/video?t={token}"
