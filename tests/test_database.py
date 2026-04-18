"""Tests para db/database.py — idempotencia del upsert y persistencia."""
from __future__ import annotations

import pytest

from db.database import (
    Adjudicacion,
    Licitacion,
)


@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """BD SQLite en directorio temporal; limpia entre tests."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "")

    # Recargar config con los nuevos env vars
    import importlib

    import config as cfg
    importlib.reload(cfg)
    import db.database as db_mod
    importlib.reload(db_mod)

    db_mod.init_db()
    return db_mod, tmp_path


def _make_lic(id_externo: str = "TEST-001", titulo: str = "Test SAP") -> Licitacion:
    return Licitacion(id_externo=id_externo, titulo=titulo)


def _make_adj(lic_id: str = "TEST-001", nombre: str = "Empresa SA") -> Adjudicacion:
    return Adjudicacion(licitacion_id=lic_id, nombre=nombre, importe_adjudicado=50000.0)


class TestUpsertLicitaciones:
    def test_inserta_nueva(self, tmp_db):
        db_mod, _ = tmp_db
        nuevas, actualizadas = db_mod.upsert_licitaciones([_make_lic()])
        assert nuevas == 1
        assert actualizadas == 0

    def test_idempotente_segunda_vez(self, tmp_db):
        db_mod, _ = tmp_db
        db_mod.upsert_licitaciones([_make_lic()])
        nuevas, actualizadas = db_mod.upsert_licitaciones([_make_lic()])
        assert nuevas == 0
        assert actualizadas == 1

    def test_actualiza_titulo(self, tmp_db):
        db_mod, _ = tmp_db
        db_mod.upsert_licitaciones([_make_lic("ID-1", "Título original")])
        db_mod.upsert_licitaciones([_make_lic("ID-1", "Título actualizado")])
        with db_mod.connect() as c:
            row = c.execute(
                "SELECT titulo FROM licitaciones WHERE id_externo = ?", ["ID-1"]
            ).fetchone()
        assert row[0] == "Título actualizado"

    def test_lista_vacia_no_falla(self, tmp_db):
        db_mod, _ = tmp_db
        nuevas, actualizadas = db_mod.upsert_licitaciones([])
        assert nuevas == 0
        assert actualizadas == 0

    def test_multiples_licitaciones(self, tmp_db):
        db_mod, _ = tmp_db
        lics = [_make_lic(f"ID-{i}") for i in range(5)]
        nuevas, actualizadas = db_mod.upsert_licitaciones(lics)
        assert nuevas == 5
        assert actualizadas == 0


class TestReplaceAdjudicaciones:
    def test_inserta_adjudicacion(self, tmp_db):
        db_mod, _ = tmp_db
        db_mod.upsert_licitaciones([_make_lic()])
        n = db_mod.replace_adjudicaciones("TEST-001", [_make_adj()])
        assert n == 1

    def test_reemplaza_adjudicaciones_existentes(self, tmp_db):
        db_mod, _ = tmp_db
        db_mod.upsert_licitaciones([_make_lic()])
        db_mod.replace_adjudicaciones("TEST-001", [_make_adj(nombre="Empresa A")])
        n = db_mod.replace_adjudicaciones(
            "TEST-001", [_make_adj(nombre="Empresa B"), _make_adj(nombre="Empresa C")]
        )
        assert n == 2
        with db_mod.connect() as c:
            count = c.execute(
                "SELECT COUNT(*) FROM adjudicaciones WHERE licitacion_id = ?",
                ["TEST-001"],
            ).fetchone()[0]
        assert count == 2

    def test_idempotente(self, tmp_db):
        db_mod, _ = tmp_db
        db_mod.upsert_licitaciones([_make_lic()])
        adjs = [_make_adj()]
        db_mod.replace_adjudicaciones("TEST-001", adjs)
        db_mod.replace_adjudicaciones("TEST-001", adjs)
        with db_mod.connect() as c:
            count = c.execute(
                "SELECT COUNT(*) FROM adjudicaciones WHERE licitacion_id = ?",
                ["TEST-001"],
            ).fetchone()[0]
        assert count == 1

    def test_lista_vacia_elimina_adjudicaciones(self, tmp_db):
        db_mod, _ = tmp_db
        db_mod.upsert_licitaciones([_make_lic()])
        db_mod.replace_adjudicaciones("TEST-001", [_make_adj()])
        db_mod.replace_adjudicaciones("TEST-001", [])
        with db_mod.connect() as c:
            count = c.execute(
                "SELECT COUNT(*) FROM adjudicaciones WHERE licitacion_id = ?",
                ["TEST-001"],
            ).fetchone()[0]
        assert count == 0
