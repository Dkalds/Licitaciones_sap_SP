"""Página Órganos — top órganos y treemap."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard.components.states import guarded_render
from dashboard.pages._base import PageContext


@guarded_render
def render(ctx: PageContext) -> None:
    df = ctx.df

    cA, cB = st.columns(2)
    with cA:
        st.subheader("Top órganos por nº de licitaciones")
        top_n = (df.groupby("organo_contratacion")
                   .agg(n=("id_externo", "count"),
                        importe=("importe", "sum"))
                   .reset_index()
                   .sort_values("n", ascending=False)
                   .head(15))
        if not top_n.empty:
            fig = px.bar(top_n.sort_values("n"), x="n",
                          y="organo_contratacion", orientation="h",
                          template=ctx.plotly_template,
                          color="importe",
                          color_continuous_scale="Greens",
                          labels={"n": "Licitaciones",
                                  "organo_contratacion": "",
                                  "importe": "Importe €"})
            fig.update_layout(height=520,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    with cB:
        st.subheader("Top órganos por importe acumulado")
        top_e = (df.groupby("organo_contratacion")
                   .agg(importe=("importe", "sum"),
                        n=("id_externo", "count"))
                   .reset_index()
                   .sort_values("importe", ascending=False)
                   .head(15))
        if not top_e.empty:
            fig = px.bar(top_e.sort_values("importe"), x="importe",
                          y="organo_contratacion", orientation="h",
                          template=ctx.plotly_template,
                          color="n", color_continuous_scale="Blues",
                          labels={"importe": "Importe €",
                                  "organo_contratacion": "",
                                  "n": "Licitaciones"})
            fig.update_layout(height=520,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Treemap: órganos → tipos proyecto → importe")
    tm = df.dropna(subset=["importe"]).copy()
    if not tm.empty:
        tm["organo_short"] = tm["organo_contratacion"].fillna("—").str[:40]
        fig = px.treemap(
            tm, path=["organo_short", "tipo_proyecto"],
            values="importe", template=ctx.plotly_template,
            color="importe", color_continuous_scale="Greens")
        fig.update_layout(height=600,
                           margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
