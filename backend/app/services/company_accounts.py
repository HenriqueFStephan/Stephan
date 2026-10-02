"""Company logins. Each account belongs to one company, and that company only.

Passwords are stored as a hash. The passage is a signature over the company id
and the username. It is not the password.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from uuid import UUID, uuid4

from app.core.config import get_settings

# Fixed accounts. Future companies get their own row and are not these two.
# internal: local tests. hse-it: the paper. Their invitations and answers do not mix.
ACCOUNTS = (
    ("admin", "admintest", "internal"),
    ("artigo", "voltarassamambanhas", "hse-it"),
)

_PASSAGE = b"stephan-company-v1"
_DUMMY_HASH = ""


class CompanySession:
    def __init__(self, company_id: UUID, username: str, slug: str, name: str) -> None:
        self.company_id = company_id
        self.username = username
        self.slug = slug
        self.name = name


def hash_password(password: str, salt: bytes | None = None) -> str:
    raw = salt if salt is not None else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), raw, 120_000)
    return f"{raw.hex()}${digest.hex()}"


def password_matches(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


def seed_company_accounts(conn) -> None:
    """Insert the two fixed accounts when they are missing. Do not reset a hash that is already there."""
    for username, password, slug in ACCOUNTS:
        company = conn.execute("SELECT id FROM companies WHERE slug = %s", (slug,)).fetchone()
        if company is None:
            continue
        existing = conn.execute(
            "SELECT id FROM company_users WHERE username = %s",
            (username,),
        ).fetchone()
        if existing is not None:
            continue
        conn.execute(
            """
            INSERT INTO company_users (id, company_id, username, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (uuid4(), company["id"], username, hash_password(password)),
        )


def authenticate(conn, username: str, password: str) -> CompanySession | None:
    row = conn.execute(
        """
        SELECT u.username, u.password_hash, c.id AS company_id, c.slug, c.name
        FROM company_users AS u
        JOIN companies AS c ON c.id = u.company_id
        WHERE u.username = %s
        """,
        (username.casefold(),),
    ).fetchone()
    if row is None:
        password_matches(password, _dummy_hash())
        return None
    if not password_matches(password, row["password_hash"]):
        return None
    return CompanySession(row["company_id"], row["username"], row["slug"], row["name"])


def issue_passage(session: CompanySession) -> str:
    payload = f"{session.company_id}.{session.username}"
    signature = hmac.new(_secret(), _PASSAGE + payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_passage(passage: str) -> tuple[UUID, str] | None:
    company_raw, separator, rest = (passage or "").partition(".")
    username, separator2, signature = rest.partition(".")
    if not separator or not separator2 or not company_raw or not username or not signature:
        return None
    try:
        company_id = UUID(company_raw)
    except ValueError:
        return None
    payload = f"{company_id}.{username}"
    expected = hmac.new(_secret(), _PASSAGE + payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return company_id, username


def session_from_passage(conn, passage: str) -> CompanySession | None:
    parsed = read_passage(passage)
    if parsed is None:
        return None
    company_id, username = parsed
    row = conn.execute(
        """
        SELECT u.username, c.id AS company_id, c.slug, c.name
        FROM company_users AS u
        JOIN companies AS c ON c.id = u.company_id
        WHERE u.username = %s
          AND c.id = %s
        """,
        (username, company_id),
    ).fetchone()
    if row is None:
        return None
    return CompanySession(row["company_id"], row["username"], row["slug"], row["name"])


def _secret() -> bytes:
    return get_settings().app_secret_key.encode("utf-8")


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if not _DUMMY_HASH:
        _DUMMY_HASH = hash_password("not-a-password", bytes(16))
    return _DUMMY_HASH
