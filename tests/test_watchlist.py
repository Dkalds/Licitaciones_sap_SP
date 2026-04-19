"""Tests para db.watchlist (CRUD + matching)."""

from __future__ import annotations


def test_crud_lifecycle(tmp_db):
    from db.watchlist import (
        WatchlistEntry,
        add_entry,
        list_entries,
        remove_entry,
    )

    e = WatchlistEntry(
        user_key="alice", cpv_prefix="72", keyword="sap", min_importe=10000.0, ccaa="Madrid"
    )
    add_entry(e)
    items = list_entries("alice")
    assert len(items) == 1
    assert items[0]["cpv_prefix"] == "72"
    assert items[0]["keyword"] == "sap"
    assert items[0]["ccaa"] == "Madrid"

    remove_entry(int(items[0]["id"]))
    assert list_entries("alice") == []


def test_add_entry_is_idempotent(tmp_db):
    from db.watchlist import WatchlistEntry, add_entry, list_entries

    entry = WatchlistEntry(user_key="u", cpv_prefix="72")
    add_entry(entry)
    add_entry(entry)
    assert len(list_entries("u")) == 1


def test_matches_licitacion_cpv_prefix():
    from db.watchlist import matches_licitacion

    entry = {"cpv_prefix": "72", "keyword": None, "min_importe": None, "ccaa": None}
    assert matches_licitacion(entry, {"cpv": "72267100-0"})
    assert not matches_licitacion(entry, {"cpv": "48700000-0"})


def test_matches_licitacion_keyword_case_insensitive():
    from db.watchlist import matches_licitacion

    entry = {"cpv_prefix": "72", "keyword": "SAP", "min_importe": None, "ccaa": None}
    assert matches_licitacion(
        entry, {"cpv": "72000000", "titulo": "Mantenimiento del sistema SAP", "descripcion": ""}
    )
    assert not matches_licitacion(entry, {"cpv": "72000000", "titulo": "oracle", "descripcion": ""})


def test_matches_licitacion_importe_filter():
    from db.watchlist import matches_licitacion

    entry = {"cpv_prefix": "72", "keyword": None, "min_importe": 100000.0, "ccaa": None}
    assert matches_licitacion(entry, {"cpv": "72000000", "importe": 200000})
    assert not matches_licitacion(entry, {"cpv": "72000000", "importe": 50000})


def test_matches_licitacion_ccaa_filter():
    from db.watchlist import matches_licitacion

    entry = {"cpv_prefix": "72", "keyword": None, "min_importe": None, "ccaa": "Cataluña"}
    assert matches_licitacion(entry, {"cpv": "72", "ccaa": "Cataluña"})
    assert not matches_licitacion(entry, {"cpv": "72", "ccaa": "Madrid"})
