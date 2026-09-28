"""Maintenance wall. Active only while BLOCKWALL_KEY is set."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.models.schemas import (
    BlockwallAck,
    BlockwallResume,
    BlockwallStatus,
    BlockwallUnlock,
    BlockwallUnlockResponse,
)

router = APIRouter(prefix="/blockwall", tags=["blockwall"])

PASSAGE_LABEL = b"stephan-blockwall-v1"


def wall_key() -> str:
    return (get_settings().blockwall_key or "").strip()


def passage_for(key: str) -> str:
    """Browser clearance. Not the password, and not reversible to it."""
    return hmac.new(key.encode("utf-8"), PASSAGE_LABEL, hashlib.sha256).hexdigest()


def secrets_match(provided: str, expected: str) -> bool:
    left = hashlib.sha256(provided.encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


@router.get("/status", response_model=BlockwallStatus)
def blockwall_status() -> BlockwallStatus:
    return BlockwallStatus(enabled=bool(wall_key()))


@router.post("/unlock", response_model=BlockwallUnlockResponse)
def blockwall_unlock(body: BlockwallUnlock) -> BlockwallUnlockResponse:
    key = wall_key()
    if not key:
        raise HTTPException(status_code=404, detail="Blockwall is not enabled")
    if not secrets_match(body.password, key):
        raise HTTPException(status_code=401, detail="Invalid password")
    return BlockwallUnlockResponse(success=True, passage=passage_for(key))


@router.post("/resume", response_model=BlockwallAck)
def blockwall_resume(body: BlockwallResume) -> BlockwallAck:
    key = wall_key()
    if not key:
        raise HTTPException(status_code=404, detail="Blockwall is not enabled")
    if not secrets_match(body.passage, passage_for(key)):
        raise HTTPException(status_code=401, detail="Invalid passage")
    return BlockwallAck(success=True)
