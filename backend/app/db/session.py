"""Connections to the local campaign database.

The URL must be PostgreSQL on this machine (or the Compose service name `db`).
A remote host is refused so a managed database URL cannot be used by mistake.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "db"})

_schema_ready = False


class DatabaseUnavailable(Exception):
    """PostgreSQL is unset, remote, or not accepting connections."""


def campaign_database_url() -> str:
    """Return the local PostgreSQL URL, or raise if it is missing or remote."""
    raw = (get_settings().database_url or "").strip()
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if not raw.startswith("postgresql://"):
        raise DatabaseUnavailable("not-postgres")
    host = (urlsplit(raw).hostname or "").lower()
    if host not in LOCAL_HOSTS:
        raise DatabaseUnavailable("not-local")
    return raw


def connect() -> psycopg.Connection:
    """Open one connection. Caller commits and closes."""
    try:
        url = campaign_database_url()
    except DatabaseUnavailable:
        raise
    try:
        return psycopg.connect(url, row_factory=dict_row, connect_timeout=3)
    except Exception as exc:
        log.warning("campaign database unavailable: %s", type(exc).__name__)
        raise DatabaseUnavailable("connect") from exc


def ensure_schema(conn: psycopg.Connection) -> None:
    """Create the campaign tables if they are not there yet."""
    global _schema_ready
    if _schema_ready:
        return
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        for statement in _statements(sql):
            cur.execute(statement)
    conn.commit()
    _schema_ready = True


def _statements(sql: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        current.append(line)
        if line.rstrip().endswith(";"):
            text = "\n".join(current).strip()
            if text:
                parts.append(text)
            current = []
    tail = "\n".join(current).strip()
    if tail:
        parts.append(tail)
    return parts
