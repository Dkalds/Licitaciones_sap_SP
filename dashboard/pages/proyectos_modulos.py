"""Página Proyectos & Módulos — módulos SAP, sunburst, CPV."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard.components.states import guarded_render
from dashboard.components.tables import data_table
from dashboard.pages._base import PageContext


@guarded_render
def render(ctx: PageContext) -> None:
    df = ctx.df

    cMod, cType = st.columns(2)

    with cMod:
        st.subheader("Módulos / productos SAP detectados")
        mod_df = df.explode("modulos")
        mod_count = (
            mod_df.groupby("modulos")
            .agg(n=("id_externo", "count"), importe=("importe", "sum"))
            .reset_index()
            .sort_values("n", ascending=False)
        )
        if not mod_count.empty:
            fig = px.bar(
                mod_count.head(15).sort_values("n"),
                x="n",
                y="modulos",
                orientation="h",
                template=ctx.plotly_template,
                color="importe",
                color_continuous_scale="YlGn",
                labels={"n": "Apariciones", "modulos": "", "importe": "Importe €"},
            )
            fig.update_layout(height=520, margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    with cType:
        st.subheader("Tipo de proyecto × Estado")  # noqa: RUF001
        cross = df.groupby(["tipo_proyecto", "estado_desc"]).size().reset_index(name="n")
        if not cross.empty:
            fig = px.sunburst(
                cross,
                path=["tipo_proyecto", "estado_desc"],
                values="n",
                template=ctx.plotly_template,
                color="n",
                color_continuous_scale="Greens",
            )
            fig.update_layout(height=520, margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top códigos CPV")
    cpv_df = (
        df.groupby(["cpv", "cpv_desc"])
        .agg(n=("id_externo", "count"), importe=("importe", "sum"))
        .reset_index()
        .sort_values("n", ascending=False)
        .head(15)
    )
    if not cpv_df.empty:
        data_table(
            cpv_df.rename(columns={"cpv_desc": "CPV", "n": "Lic.", "importe": "Importe €"})[
                ["CPV", "Lic.", "Importe €"]
            ],
            column_config={"Importe €": st.column_config.NumberColumn(format="%.0f €")},
        )
