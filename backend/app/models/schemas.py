"""Pydantic schemas for the API."""

from pydantic import BaseModel, Field, field_validator


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


class BlockwallStatus(BaseModel):
    enabled: bool


class BlockwallUnlock(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)

    @field_validator("password")
    @classmethod
    def strip_password(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("password required")
        return stripped


class BlockwallResume(BaseModel):
    passage: str = Field(..., min_length=1, max_length=128)

    @field_validator("passage")
    @classmethod
    def strip_passage(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("passage required")
        return stripped


class BlockwallAck(BaseModel):
    success: bool


class BlockwallUnlockResponse(BaseModel):
    success: bool
    passage: str


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


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    environment: str
    smtp_configured: bool = False
    studio_configured: bool = False
