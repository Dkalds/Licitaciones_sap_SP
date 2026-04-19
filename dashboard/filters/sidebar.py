"""Renderiza los filtros del sidebar y devuelve un FiltersState."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.filters.state import FiltersState


def render_sidebar_filters(df_full: pd.DataFrame) -> FiltersState:
    """Dibuja los controles de filtro en el sidebar activo y devuelve el estado."""
    st.markdown("##### Filtros")

    q = st.text_input("🔍 Buscar (título / descripción)", "", key="fs_q")

    fmin = df_full["fecha_publicacion"].min()
    fmax = df_full["fecha_publicacion"].max()
    if pd.notna(fmin) and pd.notna(fmax):
        rango = st.date_input(
            "Rango fechas",
            (fmin.date(), fmax.date()),
            min_value=fmin.date(),
            max_value=fmax.date(),
            key="fs_rango",
        )
    else:
        rango = None

    estados = st.multiselect(
        "Estado",
        sorted(df_full["estado_desc"].dropna().unique()),
        key="fs_estados",
    )
    ccaas = st.multiselect(
        "Comunidad Autónoma",
        sorted(df_full["ccaa"].dropna().unique()),
        key="fs_ccaas",
    )
    organos = st.multiselect(
        "Órgano contratante",
        sorted(df_full["organo_contratacion"].dropna().unique()),
        key="fs_organos",
    )
    tipos_proy = st.multiselect(
        "Tipo de proyecto",
        sorted(df_full["tipo_proyecto"].dropna().unique()),
        key="fs_tipos",
    )
    importe_min = st.number_input(
        "Importe mínimo (€)", min_value=0, value=0, step=10000, key="fs_imp_min"
    )

    st.divider()
    st.caption(f"Última actualización BD:\n{df_full['fecha_extraccion'].max()}")

    return FiltersState(
        q=q,
        rango=rango if isinstance(rango, tuple) and len(rango) == 2 else None,
        estados=list(estados),
        ccaas=list(ccaas),
        organos=list(organos),
        tipos_proy=list(tipos_proy),
        importe_min=int(importe_min),
    )
