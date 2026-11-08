"""Public CNPJ lookup for the signup form. Does not store the number."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import CnpjCard
from app.services.cnpj_lookup import CnpjNotFound, CnpjUnavailable, lookup_cnpj

router = APIRouter(prefix="/cnpj", tags=["cnpj"])


@router.get("/{cnpj}", response_model=CnpjCard)
def read_cnpj(cnpj: str) -> CnpjCard:
    try:
        return CnpjCard(**lookup_cnpj(cnpj))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid cnpj") from exc
    except CnpjNotFound as exc:
        raise HTTPException(status_code=404, detail="cnpj not found") from exc
    except CnpjUnavailable as exc:
        raise HTTPException(status_code=503, detail="cnpj lookup unavailable") from exc
