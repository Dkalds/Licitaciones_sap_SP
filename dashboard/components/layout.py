"""Componentes de layout — header global, footer y sidebar branding."""
from __future__ import annotations

import streamlit as st

from dashboard.data_loader import load_extracciones


def render_header() -> None:
    """Header de la app: título + botón de refresco de caché."""
    col_l, col_r = st.columns([9, 1])
    with col_l:
        st.markdown("## Licitaciones SAP · Sector Público")
    with col_r:
        if st.button("↻", use_container_width=True, help="Refrescar caché"):
            st.cache_data.clear()
            st.rerun()


def render_sidebar_brand() -> None:
    """Logo/nombre en la parte superior del sidebar."""
    st.markdown(
        '<p style="font-size:1.05rem;font-weight:600;letter-spacing:-0.02em;'
        'color:#E0E0E0;margin:0 0 1rem 2px">⬡ Licitaciones SAP</p>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Footer con metadatos de última extracción y atribución de fuente."""
    st.divider()
    ext = load_extracciones()
    if not ext.empty:
        st.caption(
            f"📦 Última extracción: "
            f"{ext.iloc[0]['fecha']} — fuente "
            f"{ext.iloc[0]['fuente']} ({ext.iloc[0]['nuevas']} nuevas)"
        )
    st.caption(
        "Fuente oficial: contrataciondelestado.es · "
        "Datos reutilizados al amparo de la Ley 37/2007"
    )
