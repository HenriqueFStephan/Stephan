"""
Application settings loaded from environment variables.

Local secrets live in debt.txt at the repo root (gitignored) or backend/.env.
See debt.txt.example for the key names.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    """Runtime configuration for the Stephan API."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", REPO_ROOT / "debt.txt"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-me"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:4200"
    # Invitation links. Not FRONTEND_URL: a local API must still send the public site.
    public_app_url: str = "https://stephan.net.br"

    # Local PostgreSQL for the HSE campaign. See docs/TOOL.md.
    # Empty until DATABASE_URL is set in debt.txt. Not a remote database.
    database_url: str = ""

    author_email: str = "author@example.com"
    author_name: str = "Stephan"

    llm_provider: str = "placeholder"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o"

    research_digest_to: str = "author@example.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    consulting_notify_to: str = ""

    # On-site /studio overlay — files GitHub issues with the solve label.
    # GITHUB_STUDIO_TOKEN is preferred so Actions' GITHUB_TOKEN is not reused locally.
    github_studio_token: str = ""
    github_token: str = ""
    github_repo: str = "HenriqueFStephan/Stephan"
    studio_access_token: str = ""
    studio_attachments_branch: str = "studio-attachments"

    # When set, the public site stays behind the maintenance wall until this
    # browser receives a clearance derived from the key. The key itself never
    # leaves the API.
    blockwall_key: str = ""

    def resolved_github_token(self) -> str:
        """PAT used to open issues and upload snips from the studio."""
        return (self.github_studio_token or self.github_token or "").strip()


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
