"""KPI bar del dashboard — extraído de app.py para reutilización y tests."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.kpi import kpi_card
from dashboard.utils.format import fmt_eur


def compute_kpis(df: pd.DataFrame) -> dict[str, float | int]:
    """Calcula los KPIs principales sobre el dataframe filtrado."""
    total = len(df)
    if total == 0:
        return {
            "total": 0,
            "importe_total": 0.0,
            "importe_medio": 0.0,
            "n_organos": 0,
            "n_ccaa": 0,
            "delta_n": 0,
            "delta_pct": 0,
            "prev30_size": 0,
        }

    importe_total = float(df["importe"].sum(skipna=True))
    importe_medio = float(df["importe"].mean(skipna=True) or 0)
    n_organos = int(df["organo_contratacion"].nunique())
    n_ccaa = int(df["ccaa"].nunique())

    hoy = pd.Timestamp.now(tz="UTC")
    fpub = df["fecha_publicacion"]
    if getattr(fpub.dt, "tz", None) is None:
        hoy = hoy.tz_localize(None)
    ult30 = df[fpub >= (hoy - pd.Timedelta(days=30))]
    prev30 = df[(fpub < (hoy - pd.Timedelta(days=30))) & (fpub >= (hoy - pd.Timedelta(days=60)))]
    delta_n = len(ult30) - len(prev30)
    delta_pct = (delta_n / len(prev30) * 100) if len(prev30) else 0.0

    return {
        "total": total,
        "importe_total": importe_total,
        "importe_medio": importe_medio,
        "n_organos": n_organos,
        "n_ccaa": n_ccaa,
        "delta_n": delta_n,
        "delta_pct": delta_pct,
        "prev30_size": len(prev30),
    }


def render_kpi_bar(df: pd.DataFrame) -> None:
    k = compute_kpis(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        delta_txt = f"{k['delta_pct']:+.0f}% últ. 30d" if k["prev30_size"] else "sin comparativa"
        st.markdown(
            kpi_card(
                "Licitaciones SAP",
                f"{k['total']:,}",
                delta=delta_txt,
                delta_up=k["delta_n"] >= 0,
                icon="📋",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            kpi_card("Importe total", fmt_eur(k["importe_total"]), icon="💰"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            kpi_card("Importe medio", fmt_eur(k["importe_medio"]), icon="📈"),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            kpi_card("Órganos distintos", f"{k['n_organos']}", icon="🏛️"), unsafe_allow_html=True
        )
    with c5:
        st.markdown(
            kpi_card("CCAA cubiertas", f"{k['n_ccaa']}/17", icon="🗺️"),
            unsafe_allow_html=True,
        )
