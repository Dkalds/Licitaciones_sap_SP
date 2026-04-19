"""Página Tendencias — evolución mensual, heatmap, histograma."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from dashboard.components.states import empty_state, guarded_render
from dashboard.pages._base import PageContext


@guarded_render
def render(ctx: PageContext) -> None:
    df = ctx.df

    st.subheader("Evolución mensual")
    g = (
        df.dropna(subset=["mes"])
        .groupby("mes")
        .agg(n=("id_externo", "count"), importe=("importe", "sum"))
        .reset_index()
    )

    if g.empty:
        empty_state(
            "📊",
            "Sin datos de evolución mensual",
            "No hay licitaciones con fecha de publicación en el rango seleccionado.",
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(
                g,
                x="mes",
                y="n",
                template=ctx.plotly_template,
                labels={"mes": "Mes", "n": "Nº licitaciones"},
                color_discrete_sequence=["#86BC25"],
            )
            fig.update_layout(height=380, margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.area(
                g,
                x="mes",
                y="importe",
                template=ctx.plotly_template,
                labels={"mes": "Mes", "importe": "Importe (€)"},
                color_discrete_sequence=["#00A3E0"],
            )
            fig.update_layout(height=380, margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Heatmap mes × estado")  # noqa: RUF001
    if not df.empty and df["mes"].notna().any():
        hm = (
            df.dropna(subset=["mes"])
            .groupby([df["mes"].dt.strftime("%Y-%m"), "estado_desc"])
            .size()
            .reset_index(name="n")
        )
        hm.columns = ["mes", "estado", "n"]
        pivot = hm.pivot(index="estado", columns="mes", values="n").fillna(0)
        fig = px.imshow(
            pivot,
            aspect="auto",
            template=ctx.plotly_template,
            color_continuous_scale="Greens",
            labels=dict(color="Licitaciones"),
        )
        fig.update_layout(height=350, margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Distribución de importes (escala log)")
    if df["importe"].notna().any():
        fig = px.histogram(
            df.dropna(subset=["importe"]).assign(importe_log=lambda x: x["importe"].clip(lower=1)),
            x="importe_log",
            log_x=True,
            nbins=40,
            template=ctx.plotly_template,
            color_discrete_sequence=["#86BC25"],
            labels={"importe_log": "Importe (€, log)"},
        )
        fig.update_layout(height=320, margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
