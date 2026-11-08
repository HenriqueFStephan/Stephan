"""Public CNPJ card for signup. Partner names from the registry are not returned."""

from __future__ import annotations

import re
import time

import httpx

from app.services.br_docs import is_cnpj, only_digits

BRASIL_API = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
MINHA_RECEITA = "https://minhareceita.org/{cnpj}"
_SOURCES = (BRASIL_API, MINHA_RECEITA)
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Stephan/cadastro (public CNPJ lookup)",
}
_TTL_SECONDS = 60 * 60
_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

_cache: dict[str, tuple[float, dict | None]] = {}


class CnpjNotFound(Exception):
    """The registry has no company for this number."""


class CnpjUnavailable(Exception):
    """The public registry could not be read."""


def clear_cache() -> None:
    _cache.clear()


def lookup_cnpj(cnpj: str) -> dict:
    digits = only_digits(cnpj)
    if not is_cnpj(digits):
        raise ValueError("invalid cnpj")
    cached = _cache.get(digits)
    if cached and time.monotonic() - cached[0] < _TTL_SECONDS:
        if cached[1] is None:
            raise CnpjNotFound()
        return cached[1]
    try:
        card = normalize(fetch_raw(digits))
    except CnpjNotFound:
        _cache[digits] = (time.monotonic(), None)
        raise
    _cache[digits] = (time.monotonic(), card)
    return card


def fetch_raw(digits: str) -> dict:
    """Try the public registries. A 404 on every source is a miss; other failures are unavailable."""
    saw_missing = False
    for template in _SOURCES:
        try:
            response = httpx.get(
                template.format(cnpj=digits),
                headers=_HEADERS,
                timeout=8.0,
            )
        except httpx.HTTPError:
            continue
        if response.status_code == 404:
            saw_missing = True
            continue
        if response.status_code != 200:
            continue
        try:
            payload = response.json()
        except ValueError:
            continue
        if isinstance(payload, dict) and _text(payload.get("razao_social"), 160):
            return payload
    if saw_missing:
        raise CnpjNotFound()
    raise CnpjUnavailable()


def normalize(payload: dict) -> dict:
    legal_name = _text(payload.get("razao_social"), 160)
    trade_name = _text(payload.get("nome_fantasia"), 160)
    if trade_name.casefold() == legal_name.casefold():
        trade_name = ""
    state = _text(payload.get("uf"), 2).upper()
    if state not in _STATES:
        state = ""
    situation = payload.get("situacao_cadastral")
    description = _text(payload.get("descricao_situacao_cadastral"), 40).upper()
    return {
        "legal_name": legal_name,
        "trade_name": trade_name,
        "cnae": _cnae(payload.get("cnae_fiscal")),
        "activity": _text(payload.get("cnae_fiscal_descricao"), 160),
        "phone": _phone(payload.get("ddd_telefone_1")),
        "postal_code": _cep(payload.get("cep")),
        "street": _text(payload.get("logradouro"), 160),
        "number": _text(payload.get("numero"), 20),
        "complement": _text(payload.get("complemento"), 80),
        "district": _text(payload.get("bairro"), 80),
        "city": _text(payload.get("municipio"), 80),
        "state": state,
        "active": situation == 2 or description == "ATIVA",
    }


def _text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _cnae(value: object) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, int) and 0 <= value <= 9_999_999:
        digits = f"{value:07d}"
    elif isinstance(value, str):
        digits = only_digits(value)
    else:
        return ""
    if len(digits) != 7:
        return ""
    return f"{digits[:4]}-{digits[4:5]}/{digits[5:]}"


def _cep(value: object) -> str:
    digits = only_digits(value) if isinstance(value, str) else ""
    return digits if len(digits) == 8 else ""


def _phone(value: object) -> str:
    if not isinstance(value, str):
        return ""
    chunks = re.findall(r"\d+", value)
    for chunk in chunks:
        if len(chunk) in (10, 11):
            return chunk
    joined = "".join(chunks)
    if len(joined) in (10, 11):
        return joined
    return ""
