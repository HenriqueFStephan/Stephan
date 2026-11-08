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


def _email_shape(value: str) -> str:
    domain = value.split("@")[-1] if "@" in value else ""
    if value.count("@") != 1 or "." not in domain:
        raise ValueError("invalid email")
    return value


_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


class CnpjCard(BaseModel):
    """Public federal registry fields used to prefill signup. Partner names are not included."""

    legal_name: str
    trade_name: str = ""
    cnae: str = ""
    activity: str = ""
    phone: str = ""
    postal_code: str = ""
    street: str = ""
    number: str = ""
    complement: str = ""
    district: str = ""
    city: str = ""
    state: str = ""
    active: bool


class OrderCreate(BaseModel):
    """Company signup. The fee follows how many forms the cycle covers, so this record does not choose a plan or a payment method. Card numbers are not a field: the API never stores them."""

    legal_name: str = Field(..., min_length=2, max_length=160)
    trade_name: str = Field(default="", max_length=160)
    cnpj: str = Field(..., min_length=14, max_length=18)
    municipal_registration: str = Field(default="", max_length=40)
    nfe_email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=20)
    postal_code: str = Field(..., min_length=8, max_length=9)
    street: str = Field(..., min_length=1, max_length=160)
    number: str = Field(..., min_length=1, max_length=20)
    complement: str = Field(default="", max_length=80)
    district: str = Field(..., min_length=1, max_length=80)
    city: str = Field(..., min_length=1, max_length=80)
    state: str = Field(..., min_length=2, max_length=2)
    cnae: str = Field(default="", max_length=12)
    headcount: int | None = Field(default=None, ge=1, le=1_000_000)
    sites: int | None = Field(default=None, ge=1, le=10_000)
    activity: str = Field(..., min_length=2, max_length=160)
    access_email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=8, max_length=200)
    accept_contract: bool = False
    privacy_ack: bool = False
    marketing: bool = False
    method: Literal["pix", "boleto", "card"] | None = None
    installments: int = Field(default=1, ge=1, le=12)
    summary_ack: bool = False
    plan: Literal["hse", "analise"] | None = None
    quoted_price_cents: int | None = Field(default=None, ge=0, le=100_000_000_00)

    @field_validator(
        "legal_name", "trade_name", "cnpj", "municipal_registration", "nfe_email",
        "phone", "postal_code", "street", "number", "complement", "district", "city",
        "state", "cnae", "activity", "access_email",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("access_email")
    @classmethod
    def email_shape(cls, value: str) -> str:
        return _email_shape(value)

    @field_validator("nfe_email")
    @classmethod
    def nfe_email_shape(cls, value: str) -> str:
        if not value:
            return ""
        return _email_shape(value)

    @field_validator("access_email")
    @classmethod
    def access_email_key(cls, value: str) -> str:
        return value.casefold()

    @field_validator("cnpj")
    @classmethod
    def cnpj_digits(cls, value: str) -> str:
        from app.services.br_docs import is_cnpj

        if not is_cnpj(value):
            raise ValueError("invalid cnpj")
        return value

    @field_validator("phone")
    @classmethod
    def phone_digits(cls, value: str) -> str:
        from app.services.br_docs import only_digits

        digits = only_digits(value)
        if digits and len(digits) not in (10, 11):
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

    @model_validator(mode="after")
    def invoice_email_follows_access(self) -> "OrderCreate":
        if not self.nfe_email:
            self.nfe_email = self.access_email
        return self

    @model_validator(mode="after")
    def installments_follow_method(self) -> "OrderCreate":
        if self.method != "card" and self.installments != 1:
            raise ValueError("installments only apply to card")
        return self

    @model_validator(mode="after")
    def quote_matches_band(self) -> "OrderCreate":
        from app.services.plans import monthly_cents

        if self.plan is None and self.quoted_price_cents is None:
            return self
        if self.plan is None or self.quoted_price_cents is None:
            raise ValueError("quoted price does not match the monthly band")
        if self.headcount is None or self.quoted_price_cents != monthly_cents(self.plan, self.headcount):
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


class CompanyDayRow(BaseModel):
    day: str
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
    first_response_on: str | None = None
    latest_response_on: str | None = None
    alpha: list[CompanyAlphaRow]
    dimensions: list[CompanyDimensionRow]
    sectors: list[CompanySectorRow]
    days: list[CompanyDayRow]
    bands: list[CompanyBandRow]


class ListQuote(BaseModel):
    """Price of a file before anything is stored or sent."""

    forms: int
    unit_cents: int
    total_cents: int
    provisional: bool = True
    methods: list[str]
    ignored_empty: int = 0
    duplicates_in_file: list[str] = []
    already_invited: list[str] = []
    invalid: list[str] = []


class FormQuote(BaseModel):
    """Provisional amount for the forms this list created. charged stays false."""

    charge_id: str
    forms: int
    unit_cents: int
    total_cents: int
    provisional: bool
    methods: list[str]
    method: str | None = None
    charged: bool = False


class ChargeMethodChoice(BaseModel):
    method: str = Field(..., min_length=1, max_length=40)


class InvitationUploadResult(BaseModel):
    round_label: str
    accepted: int
    ignored_empty: int
    duplicates_in_file: list[str]
    already_invited: list[str]
    invalid: list[str]
    not_sent: list[str] = []
    not_configured: list[str] = []
    quote: FormQuote


class InvitationRetryResult(BaseModel):
    sent: int
    not_sent: list[str] = []


class InvitationRoster(BaseModel):
    round_label: str
    invited: int
    responded_percent: int | None
    waiting_percent: int | None
    unsent: list[str] = []


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
