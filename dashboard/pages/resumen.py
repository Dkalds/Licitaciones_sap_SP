"""Página Resumen — top licitaciones, distribución y mercado."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.cards import top_card
from dashboard.components.kpi import kpi_card
from dashboard.components.states import guarded_render
from dashboard.data_loader import load_adjudicaciones
from dashboard.kpi_config import KPI_FORMULAS, KPI_THRESHOLDS
from dashboard.pages._base import PageContext
from dashboard.stats import (
    calientes_hoy,
    hhi_concentracion,
    is_anomaly,
    kpi_sparkline_series,
    lead_time_medio,
    pct_oferta_unica,
    vencen_en,
    yoy_delta,
)
from dashboard.utils.export import kpis_snapshot_csv
from dashboard.utils.format import fmt_eur


@guarded_render
def render(ctx: PageContext) -> None:
    df = ctx.df
    adj_resumen = load_adjudicaciones()

    # ── Banner "Para hoy" — señales accionables ─────────────────────
    _render_banner_hoy(df, adj_resumen)

    cL, cR = st.columns([2, 1])
    with cL:
        st.subheader("Top 10 licitaciones por importe")
        top = df.dropna(subset=["importe"]).nlargest(10, "importe")
        for _, row in top.iterrows():
            top_card(
                amount=fmt_eur(row["importe"]),
                title=str(row["titulo"]),
                meta=(
                    f"{row.get('organo_contratacion') or '—'} · "
                    f"{row.get('estado_desc') or '—'} · "
                    f"{row.get('tipo_proyecto') or '—'}"
                ),
                url=row.get("url"),
                highlight=str(row.get("modulos_str") or "—"),
            )
    with cR:
        st.subheader("Distribución por estado")
        est = (
            df.groupby("estado_desc").size().reset_index(name="n").sort_values("n", ascending=False)
        )
        if not est.empty:
            fig = px.pie(
                est,
                names="estado_desc",
                values="n",
                hole=0.55,
                template=ctx.plotly_template,
                color_discrete_sequence=ctx.color_sequence,
            )
            fig.update_traces(textposition="outside", textinfo="label+percent")
            fig.update_layout(showlegend=False, height=320, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tipos de proyecto")
        tp = (
            df.groupby("tipo_proyecto")
            .size()
            .reset_index(name="n")
            .sort_values("n", ascending=True)
        )
        if not tp.empty:
            fig = px.bar(
                tp,
                x="n",
                y="tipo_proyecto",
                orientation="h",
                template=ctx.plotly_template,
                color="n",
                color_continuous_scale="Greens",
                labels={"n": "", "tipo_proyecto": ""},
            )
            fig.update_layout(
                height=300,
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Indicadores de mercado ──
    if not adj_resumen.empty:
        ids_filt = set(df["id_externo"])
        adj_r = adj_resumen[adj_resumen["licitacion_id"].isin(ids_filt)]

        # Sparkline histórica de volumen (reutilizada en varios KPIs)
        sp_count = kpi_sparkline_series(df, metric="count", freq="W", periods=12)
        sp_sum = kpi_sparkline_series(df, metric="sum", freq="W", periods=12)

        cM1, cM2, cM3 = st.columns(3)
        with cM1:
            pct_pyme = (
                (adj_r["es_pyme"] == 1).sum() / adj_r["es_pyme"].notna().sum() * 100
                if adj_r["es_pyme"].notna().any()
                else 0
            )
            th_pyme = KPI_THRESHOLDS["pct_pyme"]
            st.markdown(
                kpi_card(
                    "% adjudicado PYMEs",
                    f"{pct_pyme:.0f}%",
                    delta="del nº de adjudicaciones",
                    delta_up=pct_pyme >= th_pyme["ok"],
                    icon="🏭",
                    tooltip=KPI_FORMULAS["pct_pyme"],
                ),
                unsafe_allow_html=True,
            )
        with cM2:
            top_cum = (
                adj_r.groupby("nombre_canonico")["importe_adjudicado"]
                .sum()
                .sort_values(ascending=False)
            )
            top10 = (top_cum.head(10).sum() / top_cum.sum() * 100) if top_cum.sum() else 0
            th_c10 = KPI_THRESHOLDS["concentracion_top10"]
            st.markdown(
                kpi_card(
                    "Concentración top 10",
                    f"{top10:.0f}%",
                    delta="del importe adjudicado",
                    delta_up=top10 < th_c10["ok"],
                    icon="📊",
                    tooltip=KPI_FORMULAS["concentracion_top10"],
                ),
                unsafe_allow_html=True,
            )
        with cM3:
            ofertas_med = adj_r["n_ofertas_recibidas"].median()
            of_txt = f"{ofertas_med:.0f}" if pd.notna(ofertas_med) else "—"
            st.markdown(
                kpi_card(
                    "Ofertas/adjudicación",
                    of_txt,
                    delta="mediana",
                    icon="📨",
                    tooltip=KPI_FORMULAS["ofertas_adj"],
                ),
                unsafe_allow_html=True,
            )

        # ── Salud competitiva del mercado ─────────────────────────
        st.markdown("#### Salud competitiva")
        cS1, cS2, cS3 = st.columns(3)

        # Lead time — adj_r ya contiene fecha_publicacion (JOIN en load_adjudicaciones).
        lt = lead_time_medio(adj_r)
        lt_txt = f"{lt:.0f} días" if lt is not None else "—"
        with cS1:
            st.markdown(
                kpi_card(
                    "Lead time pub→adj",
                    lt_txt,
                    delta="mediana",
                    icon="⏱",
                    tooltip=KPI_FORMULAS["lead_time"],
                ),
                unsafe_allow_html=True,
            )

        # HHI de concentración
        hhi_val = hhi_concentracion(adj_r)
        th_hhi = KPI_THRESHOLDS["hhi"]
        if hhi_val < th_hhi["competitivo"]:
            hhi_label = "competitivo"
            hhi_up = True
        elif hhi_val < th_hhi["moderado"]:
            hhi_label = "moderado"
            hhi_up = True
        else:
            hhi_label = "concentrado"
            hhi_up = False
        with cS2:
            st.markdown(
                kpi_card(
                    "HHI concentración",
                    f"{hhi_val:,.0f}",
                    delta=f"mercado {hhi_label}",
                    delta_up=hhi_up,
                    icon="📊",
                    tooltip=KPI_FORMULAS["hhi"],
                ),
                unsafe_allow_html=True,
            )

        # % oferta única
        ou = pct_oferta_unica(adj_r)
        th_ou = KPI_THRESHOLDS["oferta_unica"]
        with cS3:
            st.markdown(
                kpi_card(
                    "Sin competencia",
                    f"{ou:.0f}%",
                    delta="1 sola oferta",
                    delta_up=ou < th_ou["ok"],
                    icon="🔒",
                    tooltip=KPI_FORMULAS["oferta_unica"],
                ),
                unsafe_allow_html=True,
            )

        # ── Snapshot CSV ───────────────────────────────────────────
        st.markdown("")
        snapshot = {
            "% PYMEs": f"{pct_pyme:.0f}%",
            "Concentración top 10": f"{top10:.0f}%",
            "Ofertas/adjudicación (mediana)": of_txt,
            "Lead time pub→adj": lt_txt,
            "HHI concentración": f"{hhi_val:,.0f} ({hhi_label})",
            "% sin competencia": f"{ou:.0f}%",
        }
        csv_bytes = kpis_snapshot_csv(snapshot, titulo="Snapshot KPIs — Resumen")
        fname = f"kpis_resumen_{pd.Timestamp.utcnow().strftime('%Y%m%d_%H%M')}.csv"
        st.download_button(
            "📸 Descargar snapshot KPIs (CSV)",
            data=csv_bytes,
            file_name=fname,
            mime="text/csv",
            help="Exporta los indicadores actuales a CSV para pegarlos en un informe.",
        )

        # Silenciar lint sobre variables usadas en el ámbito pero no en render
        _ = (sp_count, sp_sum)


def _render_banner_hoy(df: pd.DataFrame, adj: pd.DataFrame) -> None:
    """Banner superior con señales accionables "para hoy"."""
    if df.empty:
        return

    # Watchlist matches (si hay sesión con la lista cargada)
    watchlist_ids: set[str] = set()
    matches_session = st.session_state.get("watchlist_matches") or []
    if matches_session:
        try:
            watchlist_ids = {
                str(m.get("id_externo")) for m in matches_session if m.get("id_externo")
            }
        except Exception:
            watchlist_ids = set()

    # Calculos KPI
    calientes = calientes_hoy(df, adj, watchlist_ids=watchlist_ids or None)
    vencen_48 = vencen_en(df, horas=48)
    n_wl = len(watchlist_ids)

    # Nuevas últimas 24h
    hoy = pd.Timestamp.utcnow()
    ult24h = df[df["fecha_publicacion"] >= (hoy - pd.Timedelta(hours=24))]
    n_24h = len(ult24h)

    # Anomaly: ¿las nuevas-24h son anómalas vs histórico diario?
    serie_daily = kpi_sparkline_series(df, metric="count", freq="D", periods=30)
    anom_24h = is_anomaly(float(n_24h), serie_daily[:-1] if serie_daily else [])

    # Delta vs ayer (últimas 24h anteriores)
    ayer = df[
        (df["fecha_publicacion"] >= (hoy - pd.Timedelta(hours=48)))
        & (df["fecha_publicacion"] < (hoy - pd.Timedelta(hours=24)))
    ]
    n_ayer = len(ayer)
    delta_24h = (
        f"{((n_24h - n_ayer) / n_ayer * 100):+.0f}% vs ayer" if n_ayer else f"{n_24h} nuevas"
    )

    # YoY corto para segundo KPI
    _, _, pct_n_30 = yoy_delta(df, col="importe", agg="count", days=30)

    st.markdown("#### Para hoy")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            kpi_card(
                "🆕 Nuevas 24h",
                f"{n_24h:,}",
                delta=delta_24h,
                delta_up=n_24h >= n_ayer,
                icon="🕐",
                sparkline=serie_daily,
                anomaly=anom_24h,
                tooltip="Licitaciones publicadas en las últimas 24 horas vs las 24h anteriores.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            kpi_card(
                "⏰ Vencen en 48h",
                f"{vencen_48:,}",
                delta="plazo inminente",
                delta_up=False,
                icon="⚠",
                tooltip=KPI_FORMULAS["vencen_48h"],
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            kpi_card(
                "🔥 Calientes",
                f"{len(calientes):,}",
                delta="en plazo + alto importe + bajo riesgo",
                icon="🎯",
                tooltip=KPI_FORMULAS["calientes_hoy"],
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            kpi_card(
                "🔔 Watchlist",
                f"{n_wl:,}",
                delta="matches activos",
                icon="⭐",
                tooltip="Nº de licitaciones que han disparado alguna regla de tu watchlist.",
            ),
            unsafe_allow_html=True,
        )
    st.markdown("")
    _ = pct_n_30  # reservado para futuros tooltips comparativos
