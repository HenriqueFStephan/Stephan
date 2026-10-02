"""Shared campaign database fixture."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.db.session import DatabaseUnavailable, connect, ensure_schema

LOCAL_URL = "postgresql://stephan:stephan@127.0.0.1:5432/stephan"


@pytest.fixture
def postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", LOCAL_URL)
    get_settings.cache_clear()
    import app.db.session as session

    session._schema_ready = False
    try:
        with connect() as conn:
            ensure_schema(conn)
            conn.execute("SELECT 1")
    except DatabaseUnavailable:
        get_settings.cache_clear()
        pytest.skip("local PostgreSQL is not running")
    yield
    get_settings.cache_clear()
