"""Página Observabilidad — runs del pipeline, DLQ y estado del sistema."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.kpi import kpi_card
from dashboard.components.states import empty_state, guarded_render
from dashboard.components.tables import data_table
from dashboard.pages._base import PageContext
from db.database import connect
from db.dlq import list_unresolved, mark_resolved


@guarded_render
def render(ctx: PageContext) -> None:
    st.subheader("Observabilidad")
    st.caption(
        "Estado del pipeline de extracción: runs recientes, métricas y "
        "cola de fallos pendientes de resolver."
    )

    with connect() as c:
        runs = pd.read_sql_query(
            "SELECT run_id, started_at, ended_at, duration_ms, status, "
            "months_attempted, months_ok, months_failed, "
            "licitaciones_nuevas, licitaciones_actualizadas, "
            "adjudicaciones, errores_parseo, errores_descarga, notas "
            "FROM extraction_runs ORDER BY started_at DESC LIMIT 200",
            c,
        )

    if runs.empty:
        empty_state("📉", "Sin runs registrados", "Ejecuta el pipeline para ver métricas aquí.")
        return

    runs["started_at"] = pd.to_datetime(runs["started_at"], errors="coerce")
    runs["ended_at"] = pd.to_datetime(runs["ended_at"], errors="coerce")
    runs["duration_s"] = (runs["duration_ms"] / 1000).round(1)

    last = runs.iloc[0]
    hoy = pd.Timestamp.utcnow().tz_localize(None)
    last7 = runs[runs["started_at"] >= (hoy - pd.Timedelta(days=7))]
    last30 = runs[runs["started_at"] >= (hoy - pd.Timedelta(days=30))]
    prev_week = runs[
        (runs["started_at"] >= (hoy - pd.Timedelta(days=14)))
        & (runs["started_at"] < (hoy - pd.Timedelta(days=7)))
    ]

    # ── Fila 1: estado del último run y salud reciente ────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            kpi_card(
                "Último run",
                str(last["status"]).upper(),
                delta=last["started_at"].strftime("%Y-%m-%d %H:%M")
                if pd.notna(last["started_at"])
                else "",
                icon="🏁",
            ),
            unsafe_allow_html=True,
        )
    with k2:
        ok_rate_7 = (last7["status"] == "ok").sum() / max(len(last7), 1) * 100
        st.markdown(
            kpi_card(
                "Éxito 7d",
                f"{ok_rate_7:.0f}%",
                icon="✅",
                delta=f"{len(last7)} runs",
                delta_up=ok_rate_7 >= 90,
            ),
            unsafe_allow_html=True,
        )
    with k3:
        ok_rate_30 = (last30["status"] == "ok").sum() / max(len(last30), 1) * 100
        st.markdown(
            kpi_card(
                "Éxito 30d",
                f"{ok_rate_30:.0f}%",
                icon="📅",
                delta=f"{len(last30)} runs",
                delta_up=ok_rate_30 >= 90,
            ),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            kpi_card("Duración último run", f"{last['duration_s'] or 0:.1f}s", icon="⏱"),
            unsafe_allow_html=True,
        )

    # ── Fila 2: volumen procesado (nuevas + acumulado) ────────────
    k5, k6, k7, k8 = st.columns(4)
    with k5:
        st.markdown(
            kpi_card("Nuevas último run", f"{int(last['licitaciones_nuevas']):,}", icon="🆕"),
            unsafe_allow_html=True,
        )
    with k6:
        nuevas_7d = int(last7["licitaciones_nuevas"].fillna(0).sum())
        nuevas_prev = int(prev_week["licitaciones_nuevas"].fillna(0).sum())
        delta_week_pct = (nuevas_7d - nuevas_prev) / nuevas_prev * 100 if nuevas_prev else 0.0
        st.markdown(
            kpi_card(
                "Nuevas (7d)",
                f"{nuevas_7d:,}",
                delta=f"{delta_week_pct:+.1f}% vs semana anterior",
                delta_up=delta_week_pct >= 0,
                icon="📥",
            ),
            unsafe_allow_html=True,
        )
    with k7:
        total_proc = int(runs["licitaciones_nuevas"].fillna(0).sum())
        st.markdown(
            kpi_card(
                "Total procesadas",
                f"{total_proc:,}",
                delta=f"en {len(runs)} runs",
                icon="🗃️",
            ),
            unsafe_allow_html=True,
        )
    with k8:
        avg_dur = float(last30["duration_s"].mean() or 0)
        st.markdown(
            kpi_card(
                "Duración media 30d",
                f"{avg_dur:.1f}s",
                delta="promedio por run",
                icon="⌛",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("#### Duración e incidencias por run")
    fig = px.scatter(
        runs.head(60).sort_values("started_at"),
        x="started_at",
        y="duration_s",
        color="status",
        size="licitaciones_nuevas",
        hover_data=["months_ok", "months_failed", "errores_parseo"],
        template=ctx.plotly_template,
        labels={"started_at": "Inicio", "duration_s": "Duración (s)"},
    )
    fig.update_layout(height=360, margin=dict(t=20, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Runs recientes")
    data_table(
        runs.head(50),
        height=360,
        column_config={
            "started_at": st.column_config.DatetimeColumn("Inicio"),
            "ended_at": st.column_config.DatetimeColumn("Fin"),
            "duration_s": st.column_config.NumberColumn("Duración (s)", format="%.1f"),
            "licitaciones_nuevas": st.column_config.NumberColumn("Nuevas"),
            "licitaciones_actualizadas": st.column_config.NumberColumn("Actualizadas"),
        },
    )

    st.markdown("#### Dead Letter Queue")
    failures = list_unresolved(limit=200)
    if not failures:
        st.success("No hay fallos sin resolver. ✅")
        return

    dlq_df = pd.DataFrame(failures)
    st.warning(f"{len(dlq_df)} fallos sin resolver")
    data_table(dlq_df, height=320)

    with st.expander("Marcar como resuelto"):
        ids = dlq_df["id"].astype(int).tolist()
        pick = st.selectbox("ID fallo", ids, key="dlq_pick")
        if st.button("Marcar resuelto"):
            mark_resolved(int(pick))
            st.success(f"Fallo #{pick} marcado como resuelto.")
            st.rerun()
