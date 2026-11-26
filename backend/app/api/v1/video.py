"""The tutorial video, served only to someone who holds an invitation link.

The address is /api/v1/video?t=<token>. The token is the same one that is in the
person's form link. An unknown token gets the same 404 as a missing file, so the
address does not reveal which tokens exist. The file is not listed anywhere else.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.db.session import DatabaseUnavailable, connect, ensure_schema
from app.services.invitation_video import video_file

router = APIRouter(tags=["video"])


@router.get("/video")
def tutorial_video(t: str = Query(..., min_length=8, max_length=200)) -> FileResponse:
    path = video_file()
    if path is None:
        raise HTTPException(status_code=404, detail="Not found")
    digest = hashlib.sha256(t.encode("utf-8")).hexdigest()
    try:
        with connect() as conn:
            ensure_schema(conn)
            known = conn.execute(
                "SELECT 1 FROM invitations WHERE link_token_hash = %s",
                (digest,),
            ).fetchone()
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    if known is None:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        headers={"Cache-Control": "private, max-age=3600", "X-Robots-Tag": "noindex"},
    )
