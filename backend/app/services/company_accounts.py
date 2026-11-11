"""Company logins. Each account belongs to one company, and that company only.

A company can have many accounts. Each row is one email that can sign in, with
its own password. Signup creates the first row, marks it owner, and leaves it
closed until the confirmation link is opened. The two seeded accounts are
confirmed already. The company page can add further emails as more rows on the
same company.

Passwords are stored as a hash. Confirmation and reset links store a hash of
the token. The passage is a signature over the company id and the username.
It is not the password.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.core.config import get_settings

# Fixed accounts. Future companies get their own row and are not these two.
# internal: local tests. hse-it: the paper. Their invitations and answers do not mix.
# Both emails are confirmed. A signup is not, until its confirmation link is opened.
ACCOUNTS = (
    ("admin", "admintest", "internal", "henrique.f.stephan@gmail.com"),
    ("artigo", "voltarassamambanhas", "hse-it", "celsostephan@gmail.com"),
)

CONFIRM_HOURS = 48
RESET_HOURS = 2

_PASSAGE = b"stephan-company-v1"
_DUMMY_HASH = ""


class AccessEmailTaken(Exception):
    """This email already signs in somewhere."""


class CompanyAlreadyRegistered(Exception):
    """This CNPJ already has a company row."""


class EmailUnconfirmed(Exception):
    """The password matched an account whose confirmation link is still open."""


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


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def seed_company_accounts(conn) -> None:
    """Insert the two fixed accounts when they are missing, and keep their emails confirmed.

    Do not reset a hash that is already there.
    """
    for username, password, slug, email in ACCOUNTS:
        company = conn.execute("SELECT id FROM companies WHERE slug = %s", (slug,)).fetchone()
        if company is None:
            continue
        email_norm = email.casefold()
        existing = conn.execute(
            "SELECT id FROM company_users WHERE username = %s",
            (username,),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO company_users (id, company_id, username, email, password_hash, confirmed_at)
                VALUES (%s, %s, %s, %s, %s, now())
                """,
                (uuid4(), company["id"], username, email_norm, hash_password(password)),
            )
            continue
        conn.execute(
            """
            UPDATE company_users
            SET email = %s,
                confirmed_at = COALESCE(confirmed_at, now())
            WHERE username = %s
            """,
            (email_norm, username),
        )


def provision_company_access(
    conn,
    *,
    legal_name: str,
    cnpj_digits: str,
    email: str,
    password: str,
) -> tuple[str, str]:
    """Open a company and its first access email. The password is stored only as a hash.

    The account stays closed. The returned pair is the stored email and the raw
    confirmation token. Only the hash of that token is kept.
    """
    email_norm = email.strip().casefold()
    taken = conn.execute(
        """
        SELECT 1
        FROM company_users
        WHERE lower(username) = %s
           OR (email IS NOT NULL AND lower(email) = %s)
        """,
        (email_norm, email_norm),
    ).fetchone()
    if taken is not None:
        raise AccessEmailTaken()
    slug = f"cnpj-{cnpj_digits}"
    existing = conn.execute(
        "SELECT id FROM companies WHERE cnpj = %s OR slug = %s",
        (cnpj_digits, slug),
    ).fetchone()
    if existing is not None:
        raise CompanyAlreadyRegistered()
    company_id = uuid4()
    conn.execute(
        """
        INSERT INTO companies (id, slug, name, cnpj)
        VALUES (%s, %s, %s, %s)
        """,
        (company_id, slug, legal_name, cnpj_digits),
    )
    token = secrets.token_urlsafe(32)
    conn.execute(
        """
        INSERT INTO company_users (
            id, company_id, username, email, role, password_hash,
            confirm_token_hash, confirm_expires_at
        )
        VALUES (%s, %s, %s, %s, 'owner', %s, %s, %s)
        """,
        (
            uuid4(),
            company_id,
            email_norm,
            email_norm,
            hash_password(password),
            hash_token(token),
            _until(CONFIRM_HOURS),
        ),
    )
    return email_norm, token


def authenticate(conn, username: str, password: str) -> CompanySession | None:
    key = username.strip().casefold()
    row = conn.execute(
        """
        SELECT u.username, u.password_hash, u.confirmed_at, c.id AS company_id, c.slug, c.name
        FROM company_users AS u
        JOIN companies AS c ON c.id = u.company_id
        WHERE lower(u.username) = %s
           OR (u.email IS NOT NULL AND lower(u.email) = %s)
        """,
        (key, key),
    ).fetchone()
    if row is None:
        password_matches(password, _dummy_hash())
        return None
    if not password_matches(password, row["password_hash"]):
        return None
    if row["confirmed_at"] is None:
        raise EmailUnconfirmed()
    return CompanySession(row["company_id"], row["username"], row["slug"], row["name"])


def confirm_access(conn, token: str) -> bool:
    """Open the account that holds this confirmation token. A used or old token does not."""
    row = _token_row(conn, "confirm_token_hash", "confirm_expires_at", token, confirmed=False)
    if row is None:
        return False
    conn.execute(
        """
        UPDATE company_users
        SET confirmed_at = now(),
            confirm_token_hash = NULL,
            confirm_expires_at = NULL
        WHERE id = %s
          AND confirm_token_hash = %s
          AND confirmed_at IS NULL
        """,
        (row["id"], hash_token(token.strip())),
    )
    return True


def reissue_confirmation(conn, email: str) -> tuple[str, str] | None:
    """New confirmation token for an account that is still closed. None when there is nothing to send."""
    row = _open_account(conn, email, confirmed=False)
    if row is None:
        return None
    token = secrets.token_urlsafe(32)
    conn.execute(
        """
        UPDATE company_users
        SET confirm_token_hash = %s,
            confirm_expires_at = %s
        WHERE id = %s
          AND confirmed_at IS NULL
        """,
        (hash_token(token), _until(CONFIRM_HOURS), row["id"]),
    )
    return row["email"], token


def begin_password_reset(conn, email: str) -> tuple[str, str] | None:
    """Reset token for a confirmed account. None when no message should go out."""
    row = _open_account(conn, email, confirmed=True)
    if row is None:
        return None
    token = secrets.token_urlsafe(32)
    conn.execute(
        """
        UPDATE company_users
        SET reset_token_hash = %s,
            reset_expires_at = %s
        WHERE id = %s
          AND confirmed_at IS NOT NULL
        """,
        (hash_token(token), _until(RESET_HOURS), row["id"]),
    )
    return row["email"], token


def apply_password_reset(conn, token: str, password: str) -> bool:
    """Replace the password when the reset token is still valid. The token then dies."""
    row = _token_row(conn, "reset_token_hash", "reset_expires_at", token, confirmed=True)
    if row is None:
        return False
    conn.execute(
        """
        UPDATE company_users
        SET password_hash = %s,
            reset_token_hash = NULL,
            reset_expires_at = NULL
        WHERE id = %s
          AND reset_token_hash = %s
        """,
        (hash_password(password), row["id"], hash_token(token.strip())),
    )
    return True


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


def _until(hours: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def _still_valid(expires) -> bool:
    if expires is None:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)


def _open_account(conn, email: str, *, confirmed: bool):
    key = email.strip().casefold()
    if not key:
        return None
    confirmed_sql = "u.confirmed_at IS NOT NULL" if confirmed else "u.confirmed_at IS NULL"
    return conn.execute(
        f"""
        SELECT u.id, u.email
        FROM company_users AS u
        WHERE u.email IS NOT NULL
          AND {confirmed_sql}
          AND (lower(u.email) = %s OR lower(u.username) = %s)
        """,
        (key, key),
    ).fetchone()


def _token_row(conn, hash_column: str, expires_column: str, token: str, *, confirmed: bool):
    raw = (token or "").strip()
    if not raw:
        return None
    confirmed_sql = "confirmed_at IS NOT NULL" if confirmed else "confirmed_at IS NULL"
    row = conn.execute(
        f"""
        SELECT id, {expires_column} AS expires_at
        FROM company_users
        WHERE {hash_column} = %s
          AND {confirmed_sql}
        """,
        (hash_token(raw),),
    ).fetchone()
    if row is None or not _still_valid(row["expires_at"]):
        return None
    return row


def _secret() -> bytes:
    return get_settings().app_secret_key.encode("utf-8")


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if not _DUMMY_HASH:
        _DUMMY_HASH = hash_password("not-a-password", bytes(16))
    return _DUMMY_HASH
