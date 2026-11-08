"""Public contact form. Messages stay in gitignored backend/data."""

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import DATA_DIR
from app.models.schemas import ContactAck, ContactCreate
from app.services.invitation_mail import notify_consulting

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=ContactAck)
def submit_contact(payload: ContactCreate) -> ContactAck:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = payload.model_dump()
    record["received_at"] = datetime.now(timezone.utc).isoformat()
    path = DATA_DIR / "messages.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    organization = record["organization"]
    notice = "\n".join(
        part
        for part in (
            record["name"],
            organization,
            record["email"],
            "",
            record["message"],
        )
        if part is not None
    )
    notify_consulting("Stephan — mensagem de contato", notice)
    return ContactAck(success=True, message="received")
