"""Public contact form. Messages stay in gitignored backend/data."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import DATA_DIR
from app.models.schemas import ContactAck, ContactCreate

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=ContactAck)
def submit_contact(payload: ContactCreate) -> ContactAck:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = payload.model_dump()
    record["received_at"] = datetime.now(timezone.utc).isoformat()
    path = DATA_DIR / "messages.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return ContactAck(success=True, message="received")
