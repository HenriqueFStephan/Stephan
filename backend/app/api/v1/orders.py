"""Company signup. Stores the order and does not charge a card, Pix, or boleto."""

import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import DATA_DIR
from app.models.schemas import OrderAck, OrderCreate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderAck)
def submit_order(payload: OrderCreate) -> OrderAck:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    reference = secrets.token_hex(5).upper()
    record = payload.model_dump()
    record["reference"] = reference
    record["charged"] = False
    record["received_at"] = datetime.now(timezone.utc).isoformat()
    path = DATA_DIR / "orders.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return OrderAck(success=True, reference=reference, charged=False)
