"""Pydantic schemas for the API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class StudioBlock(BaseModel):
    """One slice of a studio issue, in display order (text or image)."""

    type: str = Field(..., pattern="^(text|image)$")
    text: str = ""
    name: str = ""
    mime: str = "image/png"
    data_base64: str = ""

    @field_validator("text", "name", "mime", "data_base64")
    @classmethod
    def strip_optional(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class StudioIssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    blocks: list[StudioBlock] = Field(..., min_length=1, max_length=40)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class StudioIssueResponse(BaseModel):
    success: bool
    issue_url: str = ""
    issue_number: int = 0
    message: str = ""


class StudioStatusResponse(BaseModel):
    configured: bool
    missing: list[str] = Field(default_factory=list)


class StudioUnlockResponse(BaseModel):
    success: bool
    message: str = ""


class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    organization: str = Field(default="", max_length=160)
    email: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("name", "organization", "email", "message")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str) -> str:
        domain = value.split("@")[-1] if "@" in value else ""
        if value.count("@") != 1 or "." not in domain:
            raise ValueError("invalid email")
        return value


class ContactAck(BaseModel):
    success: bool
    message: str = ""


_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


class OrderCreate(BaseModel):
    """Company signup for a monthly plan. Card numbers are not a field: the API never stores them."""

    legal_name: str = Field(..., min_length=2, max_length=160)
    trade_name: str = Field(default="", max_length=160)
    cnpj: str = Field(..., min_length=14, max_length=18)
    municipal_registration: str = Field(default="", max_length=40)
    nfe_email: str = Field(..., min_length=3, max_length=200)
    phone: str = Field(..., min_length=10, max_length=20)
    postal_code: str = Field(..., min_length=8, max_length=9)
    street: str = Field(..., min_length=1, max_length=160)
    number: str = Field(..., min_length=1, max_length=20)
    complement: str = Field(default="", max_length=80)
    district: str = Field(..., min_length=1, max_length=80)
    city: str = Field(..., min_length=1, max_length=80)
    state: str = Field(..., min_length=2, max_length=2)
    headcount: int = Field(..., ge=1, le=1_000_000)
    sites: int = Field(..., ge=1, le=10_000)
    activity: str = Field(..., min_length=2, max_length=160)
    rep_name: str = Field(..., min_length=2, max_length=120)
    rep_cpf: str = Field(..., min_length=11, max_length=14)
    rep_role: str = Field(..., min_length=2, max_length=80)
    rep_email: str = Field(..., min_length=3, max_length=200)
    rep_phone: str = Field(..., min_length=10, max_length=20)
    contact_name: str = Field(..., min_length=2, max_length=120)
    contact_role: str = Field(..., min_length=2, max_length=80)
    contact_email: str = Field(..., min_length=3, max_length=200)
    contact_phone: str = Field(..., min_length=10, max_length=20)
    accept_contract: bool
    privacy_ack: bool
    marketing: bool = False
    method: Literal["pix", "boleto", "card"]
    installments: int = Field(default=1, ge=1, le=12)
    summary_ack: bool
    plan: Literal["hse", "analise"]
    quoted_price_cents: int = Field(..., ge=0, le=100_000_000_00)

    @field_validator(
        "legal_name", "trade_name", "cnpj", "municipal_registration", "nfe_email",
        "phone", "postal_code", "street", "number", "complement", "district", "city",
        "state", "activity", "rep_name", "rep_cpf", "rep_role", "rep_email", "rep_phone",
        "contact_name", "contact_role", "contact_email", "contact_phone",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("nfe_email", "rep_email", "contact_email")
    @classmethod
    def email_shape(cls, value: str) -> str:
        domain = value.split("@")[-1] if "@" in value else ""
        if value.count("@") != 1 or "." not in domain:
            raise ValueError("invalid email")
        return value

    @field_validator("cnpj")
    @classmethod
    def cnpj_digits(cls, value: str) -> str:
        from app.services.br_docs import is_cnpj

        if not is_cnpj(value):
            raise ValueError("invalid cnpj")
        return value

    @field_validator("rep_cpf")
    @classmethod
    def cpf_digits(cls, value: str) -> str:
        from app.services.br_docs import is_cpf

        if not is_cpf(value):
            raise ValueError("invalid cpf")
        return value

    @field_validator("phone", "rep_phone", "contact_phone")
    @classmethod
    def phone_digits(cls, value: str) -> str:
        from app.services.br_docs import only_digits

        if len(only_digits(value)) not in (10, 11):
            raise ValueError("invalid phone")
        return value

    @field_validator("postal_code")
    @classmethod
    def cep_digits(cls, value: str) -> str:
        from app.services.br_docs import only_digits

        if len(only_digits(value)) != 8:
            raise ValueError("invalid cep")
        return value

    @field_validator("state")
    @classmethod
    def state_code(cls, value: str) -> str:
        code = value.upper()
        if code not in _STATES:
            raise ValueError("invalid state")
        return code

    @field_validator("accept_contract", "privacy_ack", "summary_ack")
    @classmethod
    def must_accept(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("acceptance required")
        return value

    @model_validator(mode="after")
    def installments_follow_method(self) -> "OrderCreate":
        if self.method != "card" and self.installments != 1:
            raise ValueError("installments only apply to card")
        return self

    @model_validator(mode="after")
    def quote_matches_band(self) -> "OrderCreate":
        from app.services.plans import monthly_cents

        if self.quoted_price_cents != monthly_cents(self.plan, self.headcount):
            raise ValueError("quoted price does not match the monthly band")
        return self


class OrderAck(BaseModel):
    success: bool
    reference: str
    charged: bool = False


class CompanyLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=1, max_length=200)

    @field_validator("username", "password")
    @classmethod
    def strip_login(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("required")
        return stripped


class CompanyLoginResponse(BaseModel):
    success: bool
    passage: str
    company_slug: str
    company_name: str


class ToolAccessRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=200)


class ToolDraft(BaseModel):
    place: Literal["profile", "ask"]
    index: int = Field(..., ge=0, le=34)
    demographics: dict = Field(default_factory=dict)
    answers: list[int | None] = Field(..., min_length=35, max_length=35)


class ToolAccessResponse(BaseModel):
    state: str
    draft: ToolDraft | None = None


class ToolSubmitRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=200)
    answers: list[int] = Field(..., min_length=35, max_length=35)
    demographics: dict = Field(default_factory=dict)


class ToolDraftRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=200)
    place: Literal["profile", "ask"]
    index: int = Field(0, ge=0, le=34)
    demographics: dict = Field(default_factory=dict)
    answers: list[int | None] = Field(..., min_length=35, max_length=35)


class ToolSubmitResponse(BaseModel):
    saved: bool


class CompanyAlphaRow(BaseModel):
    id: str
    alpha: float | None
    items: int
    n: int
    reading: str
    mean: float | None = None


class CompanyDimensionRow(BaseModel):
    id: str
    mean: float


class CompanySectorMean(BaseModel):
    id: str
    mean: float


class CompanySectorRow(BaseModel):
    id: str
    count: int
    means: list[CompanySectorMean]


class CompanyWeekRow(BaseModel):
    week: str
    count: int


class CompanyBandRow(BaseModel):
    id: str
    urgent: int
    improve: int
    good: int
    maintain: int


class CompanyOverview(BaseModel):
    source: str
    company_id: str
    respondent_count: int
    first_response_on: str
    latest_response_on: str
    alpha: list[CompanyAlphaRow]
    dimensions: list[CompanyDimensionRow]
    sectors: list[CompanySectorRow]
    weeks: list[CompanyWeekRow]
    bands: list[CompanyBandRow]


class InvitationUploadResult(BaseModel):
    round_label: str
    accepted: int
    ignored_empty: int
    duplicates_in_file: list[str]
    already_invited: list[str]
    invalid: list[str]
    not_sent: list[str] = []


class InvitationRoster(BaseModel):
    round_label: str
    invited: int
    responded_percent: int | None
    waiting_percent: int | None


class CompanyRoundRow(BaseModel):
    label: str
    opened_on: str
    closed_on: str | None
    invited: int
    responded_percent: int | None
    waiting_percent: int | None
    latest_response_on: str | None


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    environment: str
    smtp_configured: bool = False
    studio_configured: bool = False
