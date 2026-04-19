"""Dashboard Streamlit — Licitaciones SAP del Sector Público."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dashboard.auth import check_password
from dashboard.components.layout import (
    render_footer,
    render_header,
    render_sidebar_brand,
)
from dashboard.components.navigation import (
    active_filters_chips,
    breadcrumb,
    sub_nav,
)
from dashboard.components.states import empty_state
from dashboard.data_loader import invalidate_caches, load_dataframe
from dashboard.filters import (
    FiltersState,
    apply_filters,
    render_sidebar_filters,
)
from dashboard.kpi_bar import render_kpi_bar
from dashboard.pages import PAGE_REGISTRY
from dashboard.pages._base import PageContext
from dashboard.query_params_sync import load_initial, sync_to_url
from dashboard.router import SECTION_ICONS, SECTIONS
from dashboard.theme import (
    TOKENS,
    build_css,
    get_color_sequence,
    register_plotly_template,
)

st.set_page_config(
    page_title="Licitaciones SAP · Sector Público",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(build_css(TOKENS), unsafe_allow_html=True)
st.markdown(
    '<a class="skip-link" href="#main">Saltar al contenido</a>',
    unsafe_allow_html=True,
)

check_password()

PLOTLY_TEMPLATE = register_plotly_template(TOKENS)
COLOR_SEQUENCE = get_color_sequence(TOKENS)

render_header()

df_full = load_dataframe()

if df_full.empty:
    empty_state(
        "📭",
        "Sin datos en la base de datos",
        "Ejecuta el pipeline para importar licitaciones.",
        cta_label="Ver comando de carga",
        cta_cb=lambda: st.code("python -m scheduler.run_update --backfill 2024 1"),  # type: ignore[arg-type]
    )
    st.stop()

load_initial(df_full)

with st.sidebar:
    render_sidebar_brand()
    section = st.radio(
        "nav",
        list(SECTIONS.keys()),
        format_func=lambda x: f"{SECTION_ICONS[x]}  {x}",
        label_visibility="collapsed",
        key="nav_section",
    )
    st.divider()
    filters: FiltersState = render_sidebar_filters(df_full)
    st.divider()
    compact = st.toggle("📰 Modo compacto", key="density_compact", value=False)
    if st.button(
        "🔄 Refrescar datos",
        use_container_width=True,
        help="Invalida el caché y recarga desde la BD",
    ):
        invalidate_caches()
        st.rerun()

if compact:
    st.markdown(
        "<style>:root { --density: 0.78; }</style>",
        unsafe_allow_html=True,
    )

df = apply_filters(df_full, filters)
sync_to_url(filters)
render_kpi_bar(df)

st.markdown("")

pages = SECTIONS[section]
page = sub_nav(pages, key=f"nav_page_{section}")
breadcrumb(section, page)
active_filters_chips(filters)
st.markdown("")

ctx = PageContext(
    df=df,
    df_full=df_full,
    filters=filters,
    tokens=TOKENS,
    plotly_template=PLOTLY_TEMPLATE,
    color_sequence=COLOR_SEQUENCE,
)
PAGE_REGISTRY[page](ctx)

render_footer()
