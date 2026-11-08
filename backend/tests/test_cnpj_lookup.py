"""CNPJ lookup returns the public card and never the partner list."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.cnpj_lookup import CnpjNotFound, CnpjUnavailable, clear_cache

client = TestClient(app)

CNPJ = "00000000000191"


def setup_function():
    clear_cache()


def card(**overrides):
    body = {
        "razao_social": "BANCO DO BRASIL SA",
        "nome_fantasia": "DIRECAO GERAL",
        "cnae_fiscal": 6422100,
        "cnae_fiscal_descricao": "Bancos múltiplos, com carteira comercial",
        "cep": "70040-912",
        "logradouro": "SAUN QUADRA 5",
        "numero": "SN",
        "complemento": "ANDAR 1",
        "bairro": "ASA NORTE",
        "municipio": "BRASILIA",
        "uf": "df",
        "ddd_telefone_1": "(61) 3493-9002",
        "email": "nao-usar@example.com",
        "situacao_cadastral": 2,
        "descricao_situacao_cadastral": "ATIVA",
        "qsa": [{"nome_socio": "Alguém", "cnpj_cpf_do_socio": "00000000000"}],
    }
    body.update(overrides)
    return body


def test_lookup_returns_the_company_and_address_without_partners(monkeypatch):
    monkeypatch.setattr("app.services.cnpj_lookup.fetch_raw", lambda digits: card())
    response = client.get(f"/api/v1/cnpj/{CNPJ}")
    assert response.status_code == 200
    body = response.json()
    assert body["legal_name"] == "BANCO DO BRASIL SA"
    assert body["trade_name"] == "DIRECAO GERAL"
    assert body["cnae"] == "6422-1/00"
    assert body["activity"] == "Bancos múltiplos, com carteira comercial"
    assert body["phone"] == "6134939002"
    assert body["postal_code"] == "70040912"
    assert body["state"] == "DF"
    assert body["active"] is True
    assert "email" not in body
    assert "qsa" not in body


def test_lookup_pads_a_cnae_that_starts_with_zero(monkeypatch):
    monkeypatch.setattr(
        "app.services.cnpj_lookup.fetch_raw",
        lambda digits: card(cnae_fiscal=111301),
    )
    response = client.get(f"/api/v1/cnpj/{CNPJ}")
    assert response.status_code == 200
    assert response.json()["cnae"] == "0111-3/01"


def test_lookup_drops_a_trade_name_that_repeats_the_legal_name(monkeypatch):
    monkeypatch.setattr(
        "app.services.cnpj_lookup.fetch_raw",
        lambda digits: card(nome_fantasia="banco do brasil sa"),
    )
    response = client.get(f"/api/v1/cnpj/{CNPJ}")
    assert response.status_code == 200
    assert response.json()["trade_name"] == ""


def test_lookup_marks_a_closed_company_and_still_returns_the_card(monkeypatch):
    monkeypatch.setattr(
        "app.services.cnpj_lookup.fetch_raw",
        lambda digits: card(situacao_cadastral=8, descricao_situacao_cadastral="BAIXADA"),
    )
    response = client.get(f"/api/v1/cnpj/{CNPJ}")
    assert response.status_code == 200
    assert response.json()["active"] is False
    assert response.json()["legal_name"] == "BANCO DO BRASIL SA"


def test_lookup_rejects_a_bad_cnpj(monkeypatch):
    def fail(digits):
        raise AssertionError("the registry should not be called")

    monkeypatch.setattr("app.services.cnpj_lookup.fetch_raw", fail)
    response = client.get("/api/v1/cnpj/11111111111111")
    assert response.status_code == 422


def test_lookup_reports_a_miss(monkeypatch):
    def missing(digits):
        raise CnpjNotFound()

    monkeypatch.setattr("app.services.cnpj_lookup.fetch_raw", missing)
    response = client.get(f"/api/v1/cnpj/{CNPJ}")
    assert response.status_code == 404


def test_lookup_reports_when_the_registry_is_down(monkeypatch):
    def down(digits):
        raise CnpjUnavailable()

    monkeypatch.setattr("app.services.cnpj_lookup.fetch_raw", down)
    response = client.get(f"/api/v1/cnpj/{CNPJ}")
    assert response.status_code == 503
