"""Fixtures compartidos para aislar la BD en tests."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """BD SQLite temporal con migraciones aplicadas. Aislada por test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "")

    import config as cfg

    importlib.reload(cfg)
    import db.database as db_mod

    importlib.reload(db_mod)
    import db.migrations as mig

    importlib.reload(mig)
    import db.dlq as dlq

    importlib.reload(dlq)
    import db.watchlist as wl

    importlib.reload(wl)

    db_mod.init_db()
    return db_mod, tmp_path
