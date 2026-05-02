"""Tests de la API REST (FastAPI + httpx TestClient)."""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient


def _client(tmp_db, monkeypatch, *, api_key: str | None = None):
    """Construye un TestClient con la BD aislada."""
    if api_key is None:
        monkeypatch.delenv("API_KEY", raising=False)
    else:
        monkeypatch.setenv("API_KEY", api_key)
    import config as cfg

    importlib.reload(cfg)
    import api.main as api_mod

    importlib.reload(api_mod)
    return TestClient(api_mod.app)


def test_healthz_returns_status(tmp_db, monkeypatch):
    client = _client(tmp_db, monkeypatch)
    r = client.get("/healthz")
    assert r.status_code == 200
    payload = r.json()
    assert "status" in payload


def test_list_licitaciones_empty(tmp_db, monkeypatch):
    client = _client(tmp_db, monkeypatch)
    r = client.get("/v1/licitaciones")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["items"] == []


def test_list_licitaciones_with_data(tmp_db, monkeypatch):
    db_mod, _ = tmp_db
    db_mod.upsert_licitaciones(
        [db_mod.Licitacion(id_externo="X-1", titulo="SAP Test", importe=1000.0, cpv="72212000")]
    )
    client = _client(tmp_db, monkeypatch)
    r = client.get("/v1/licitaciones?cpv_prefix=72&limit=10")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["items"][0]["id_externo"] == "X-1"


def test_list_licitaciones_min_importe_filter(tmp_db, monkeypatch):
    db_mod, _ = tmp_db
    db_mod.upsert_licitaciones(
        [
            db_mod.Licitacion(id_externo="small", titulo="s", importe=100.0),
            db_mod.Licitacion(id_externo="big", titulo="b", importe=999999.0),
        ]
    )
    client = _client(tmp_db, monkeypatch)
    r = client.get("/v1/licitaciones?min_importe=1000")
    assert r.status_code == 200
    ids = [i["id_externo"] for i in r.json()["items"]]
    assert ids == ["big"]


def test_api_key_protection(tmp_db, monkeypatch):
    client = _client(tmp_db, monkeypatch, api_key="topsecret")
    r = client.get("/v1/licitaciones")
    assert r.status_code == 401
    r = client.get("/v1/licitaciones", headers={"X-API-Key": "topsecret"})
    assert r.status_code == 200


def test_cpv_prefix_validation_rejects_injection(tmp_db, monkeypatch):
    client = _client(tmp_db, monkeypatch)
    r = client.get("/v1/licitaciones?cpv_prefix=72' OR 1=1--")
    assert r.status_code == 422


def test_list_runs(tmp_db, monkeypatch):
    from observability.metrics import record_run

    with record_run("run-x") as m:
        m.months_ok = 1

    client = _client(tmp_db, monkeypatch)
    r = client.get("/v1/runs")
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["run_id"] == "run-x" for i in items)
