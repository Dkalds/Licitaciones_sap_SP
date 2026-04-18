"""Página Resumen — top licitaciones, distribución y mercado."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.cards import top_card
from dashboard.components.kpi import kpi_card
from dashboard.components.states import empty_state, guarded_render
from dashboard.data_loader import load_adjudicaciones
from dashboard.pages._base import PageContext
from dashboard.utils.format import fmt_eur


@guarded_render
def render(ctx: PageContext) -> None:
    df = ctx.df

    cL, cR = st.columns([2, 1])
    with cL:
        st.subheader("Top 10 licitaciones por importe")
        top = (df.dropna(subset=["importe"])
                 .nlargest(10, "importe"))
        for _, row in top.iterrows():
            top_card(
                amount=fmt_eur(row["importe"]),
                title=str(row["titulo"]),
                meta=(
                    f'{row.get("organo_contratacion") or "—"} · '
                    f'{row.get("estado_desc") or "—"} · '
                    f'{row.get("tipo_proyecto") or "—"}'
                ),
                url=row.get("url"),
                highlight=str(row.get("modulos_str") or "—"),
            )
    with cR:
        st.subheader("Distribución por estado")
        est = (df.groupby("estado_desc").size()
                  .reset_index(name="n")
                  .sort_values("n", ascending=False))
        if not est.empty:
            fig = px.pie(est, names="estado_desc", values="n", hole=0.55,
                          template=ctx.plotly_template,
                          color_discrete_sequence=ctx.color_sequence)
            fig.update_traces(textposition="outside", textinfo="label+percent")
            fig.update_layout(showlegend=False, height=320,
                               margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tipos de proyecto")
        tp = (df.groupby("tipo_proyecto").size()
                .reset_index(name="n").sort_values("n", ascending=True))
        if not tp.empty:
            fig = px.bar(tp, x="n", y="tipo_proyecto", orientation="h",
                          template=ctx.plotly_template,
                          color="n", color_continuous_scale="Greens",
                          labels={"n": "", "tipo_proyecto": ""})
            fig.update_layout(height=300, showlegend=False,
                               coloraxis_showscale=False,
                               margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    # ── Indicadores de mercado ──
    adj_resumen = load_adjudicaciones()
    if not adj_resumen.empty:
        ids_filt = set(df["id_externo"])
        adj_r = adj_resumen[adj_resumen["licitacion_id"].isin(ids_filt)]
        cM1, cM2, cM3 = st.columns(3)
        with cM1:
            pct_pyme = ((adj_r["es_pyme"] == 1).sum() /
                         adj_r["es_pyme"].notna().sum() * 100
                         if adj_r["es_pyme"].notna().any() else 0)
            st.markdown(kpi_card("% adjudicado PYMEs",
                                  f"{pct_pyme:.0f}%", icon="🏭"),
                         unsafe_allow_html=True)
        with cM2:
            top_cum = (adj_r.groupby("nombre_canonico")["importe_adjudicado"]
                          .sum().sort_values(ascending=False))
            top10 = (top_cum.head(10).sum() /
                      top_cum.sum() * 100) if top_cum.sum() else 0
            st.markdown(kpi_card("Concentración top 10",
                                  f"{top10:.0f}%",
                                  delta="del importe adjudicado",
                                  delta_up=top10 < 60, icon="📊"),
                         unsafe_allow_html=True)
        with cM3:
            ofertas_med = adj_r["n_ofertas_recibidas"].median()
            of_txt = f"{ofertas_med:.0f}" if pd.notna(ofertas_med) else "—"
            st.markdown(kpi_card("Ofertas/adjudicación",
                                  of_txt,
                                  delta="mediana", icon="📨"),
                         unsafe_allow_html=True)
