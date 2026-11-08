"""Company signup. Stores the order and does not charge a card, Pix, or boleto."""

import json
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.config import DATA_DIR
from app.db.session import DatabaseUnavailable, connect, ensure_schema
from app.models.schemas import OrderAck, OrderCreate
from app.services.br_docs import only_digits
from app.services.company_accounts import (
    AccessEmailTaken,
    CompanyAlreadyRegistered,
    provision_company_access,
)
from app.services.invitation_mail import notify_consulting

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderAck)
def submit_order(payload: OrderCreate) -> OrderAck:
    try:
        with connect() as conn:
            ensure_schema(conn)
            provision_company_access(
                conn,
                legal_name=payload.legal_name,
                cnpj_digits=only_digits(payload.cnpj),
                email=payload.access_email,
                password=payload.password,
            )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from exc
    except AccessEmailTaken as exc:
        raise HTTPException(status_code=409, detail={"code": "email_taken"}) from exc
    except CompanyAlreadyRegistered as exc:
        raise HTTPException(status_code=409, detail={"code": "cnpj_taken"}) from exc
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    reference = secrets.token_hex(5).upper()
    record = payload.model_dump(exclude={"password"})
    record["reference"] = reference
    record["charged"] = False
    record["received_at"] = datetime.now(timezone.utc).isoformat()
    path = DATA_DIR / "orders.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    lines = [
        f"Referência: {reference}",
        f"Empresa: {record['legal_name']}",
    ]
    if record.get("plan"):
        lines.append(f"Plano: {record['plan']}")
    lines.append(f"Acesso: {record['access_email']}")
    notify_consulting(f"Stephan — cadastro {reference}", "\n".join(lines))
    return OrderAck(success=True, reference=reference, charged=False)
