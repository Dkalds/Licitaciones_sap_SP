"""Página Geografía — reparto por CCAA y provincias."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard.components.states import empty_state, guarded_render
from dashboard.components.tables import data_table
from dashboard.pages._base import PageContext


@guarded_render
def render(ctx: PageContext) -> None:
    df = ctx.df

    geo = (df.dropna(subset=["ccaa"])
             .groupby("ccaa")
             .agg(n=("id_externo", "count"),
                  importe=("importe", "sum"))
             .reset_index())

    cM, cT = st.columns([2, 1])
    with cM:
        st.subheader("Reparto por Comunidad Autónoma")
        if not geo.empty:
            fig = px.bar(geo.sort_values("n"), x="n", y="ccaa",
                          orientation="h", template=ctx.plotly_template,
                          color="importe", color_continuous_scale="Greens",
                          labels={"n": "Licitaciones", "ccaa": "",
                                  "importe": "Importe €"})
            fig.update_layout(height=600,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            empty_state(
                "🗺️",
                "Sin datos geográficos",
                "Re-ejecuta el pipeline tras la actualización del parser para poblar CCAA y provincias.",
            )

    with cT:
        st.subheader("Top provincias")
        prov = (df.dropna(subset=["provincia"])
                  .groupby("provincia")
                  .agg(n=("id_externo", "count"),
                       importe=("importe", "sum"))
                  .reset_index()
                  .sort_values("n", ascending=False)
                  .head(15))
        if not prov.empty:
            data_table(
                prov.rename(columns={"n": "Lic.",
                                       "importe": "Importe €"}),
                column_config={
                    "Importe €": st.column_config.NumberColumn(
                        format="%.0f €")},
            )
