"""Tests para dashboard.kpi_bar.compute_kpis."""

from __future__ import annotations

import pandas as pd

from dashboard.kpi_bar import compute_kpis


def _mk_df(n_recent: int, n_prev: int) -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC")
    rows = []
    for i in range(n_recent):
        rows.append(
            {
                "fecha_publicacion": now - pd.Timedelta(days=10 + i),
                "importe": 1000.0 * (i + 1),
                "organo_contratacion": f"Org-{i % 3}",
                "ccaa": f"CCAA-{i % 4}",
            }
        )
    for i in range(n_prev):
        rows.append(
            {
                "fecha_publicacion": now - pd.Timedelta(days=40 + i),
                "importe": 500.0,
                "organo_contratacion": "Org-old",
                "ccaa": "CCAA-old",
            }
        )
    return pd.DataFrame(rows)


def test_compute_kpis_basic_totals():
    df = _mk_df(5, 3)
    k = compute_kpis(df)
    assert k["total"] == 8
    assert k["n_organos"] == 4
    assert k["n_ccaa"] == 5
    assert k["importe_total"] > 0
    assert k["importe_medio"] > 0


def test_compute_kpis_delta_positive():
    df = _mk_df(10, 5)
    k = compute_kpis(df)
    assert k["delta_n"] == 5
    assert k["delta_pct"] == 100.0


def test_compute_kpis_empty_df_is_safe():
    df = pd.DataFrame(columns=["fecha_publicacion", "importe", "organo_contratacion", "ccaa"])
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"])
    k = compute_kpis(df)
    assert k["total"] == 0
    assert k["importe_total"] == 0.0
    assert k["n_organos"] == 0
    assert k["delta_pct"] == 0
