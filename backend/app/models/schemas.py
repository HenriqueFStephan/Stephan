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


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    environment: str
    smtp_configured: bool = False
    studio_configured: bool = False
