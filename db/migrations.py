"""Sistema simple de migraciones basado en tabla ``schema_version``.

Cada migración es una tupla ``(version, description, sql)``. Se aplican en
orden ascendente y la versión actual queda registrada en ``schema_version``.

Diseñado para proyectos pequeños donde un Alembic completo es overkill pero
mantener un historial auditable sigue siendo importante.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from observability.logging import get_logger

log = get_logger(__name__)


# Lista append-only: nunca modificar una migración ya desplegada — añadir otra.
MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "baseline_and_run_metrics",
        """
        CREATE TABLE IF NOT EXISTS extraction_runs (
            run_id                  TEXT PRIMARY KEY,
            started_at              TEXT NOT NULL,
            ended_at                TEXT,
            duration_ms             INTEGER,
            status                  TEXT NOT NULL,
            months_attempted        INTEGER DEFAULT 0,
            months_ok               INTEGER DEFAULT 0,
            months_failed           INTEGER DEFAULT 0,
            licitaciones_nuevas     INTEGER DEFAULT 0,
            licitaciones_actualizadas INTEGER DEFAULT 0,
            adjudicaciones          INTEGER DEFAULT 0,
            errores_parseo          INTEGER DEFAULT 0,
            errores_descarga        INTEGER DEFAULT 0,
            notas                   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_runs_started ON extraction_runs(started_at);
        CREATE INDEX IF NOT EXISTS idx_runs_status  ON extraction_runs(status);

        CREATE TABLE IF NOT EXISTS failed_extractions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          TEXT,
            fuente          TEXT NOT NULL,
            scope           TEXT,
            error_type      TEXT,
            error_message   TEXT,
            payload_ref     TEXT,
            retry_count     INTEGER DEFAULT 0,
            resolved_at     TEXT,
            created_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_fail_run ON failed_extractions(run_id);
        CREATE INDEX IF NOT EXISTS idx_fail_unresolved ON failed_extractions(resolved_at);
        """,
    ),
    (
        2,
        "user_watchlist",
        """
        CREATE TABLE IF NOT EXISTS watchlist_cpv (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key        TEXT NOT NULL,
            cpv_prefix      TEXT NOT NULL,
            keyword         TEXT,
            min_importe     REAL,
            ccaa            TEXT,
            created_at      TEXT NOT NULL,
            UNIQUE(user_key, cpv_prefix, keyword, ccaa)
        );
        CREATE INDEX IF NOT EXISTS idx_wl_user ON watchlist_cpv(user_key);
        """,
    ),
    (
        3,
        "watchlist_last_notified",
        """
        ALTER TABLE watchlist_cpv ADD COLUMN last_notified_at TEXT;
        """,
    ),
]


def _ensure_version_table(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        )
        """
    )


def current_version(conn: Any) -> int:
    _ensure_version_table(conn)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0] or 0)


def apply_pending(conn: Any) -> list[int]:
    """Aplica todas las migraciones pendientes. Devuelve las versiones aplicadas."""
    applied: list[int] = []
    _ensure_version_table(conn)
    current = current_version(conn)
    for version, description, sql in sorted(MIGRATIONS, key=lambda m: m[0]):
        if version <= current:
            continue
        log.info("migration_applying", version=version, description=description)
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)
        conn.execute(
            "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
            (version, description, datetime.utcnow().isoformat()),
        )
        applied.append(version)
    if applied:
        log.info("migrations_applied", versions=applied)
    return applied
