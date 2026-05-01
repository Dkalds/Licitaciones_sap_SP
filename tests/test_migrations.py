"""Tests para db.migrations: aplicación idempotente del esquema."""

from __future__ import annotations

import sqlite3

from db.migrations import MIGRATIONS, apply_pending, current_version


def _fresh_conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def test_current_version_starts_at_zero():
    conn = _fresh_conn()
    assert current_version(conn) == 0


def test_apply_pending_creates_all_migrations():
    conn = _fresh_conn()
    applied = apply_pending(conn)
    assert applied == sorted(m[0] for m in MIGRATIONS)
    assert current_version(conn) == max(m[0] for m in MIGRATIONS)


def test_apply_pending_is_idempotent():
    conn = _fresh_conn()
    apply_pending(conn)
    applied_second = apply_pending(conn)
    assert applied_second == []


def test_expected_tables_exist():
    conn = _fresh_conn()
    apply_pending(conn)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"extraction_runs", "failed_extractions", "watchlist_cpv", "schema_version"}.issubset(
        names
    )
    # Nuevas tablas del carril diario
    assert "ingestion_cursors" in names
    assert "licitaciones_history" in names
