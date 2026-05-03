"""Dashboard Streamlit — Licitaciones SAP del Sector Público."""

from __future__ import annotations

import streamlit as st

from dashboard.auth import check_password
from dashboard.components.layout import (render_footer, render_header,
                                          render_sidebar_brand)
from dashboard.components.navigation import (active_filters_chips, breadcrumb,
                                              sub_nav)
from dashboard.components.states import empty_state
from dashboard.data_loader import load_dataframe
from dashboard.filters import FiltersState, apply_filters, render_sidebar_filters
from dashboard.kpi_bar import render_kpi_bar
from dashboard.pages import PAGE_REGISTRY
from dashboard.pages._base import PageContext
from dashboard.router import SECTIONS
from dashboard.theme import (COMPACT_DENSITY_CSS, TOKENS, build_css,
                              get_color_sequence, register_plotly_template)

# ── Config & estilo ──────────────────────────────────────────────────────
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

# ── Autenticación ────────────────────────────────────────────────────────
check_password()

# ── Plotly premium template ─────────────────────────────────────────────
PLOTLY_TEMPLATE = register_plotly_template(TOKENS)
COLOR_SEQUENCE = get_color_sequence(TOKENS)

# ── Carga de datos (necesaria antes del header para 'última actualización') ──
df_full = load_dataframe()

# ── Header ──────────────────────────────────────────────────────────────
last_updated = df_full["fecha_extraccion"].max() if not df_full.empty else None
render_header(last_updated=last_updated)

if df_full.empty:
    empty_state(
        "inbox",
        "Sin datos en la base de datos",
        "Ejecuta el pipeline para importar licitaciones.",
        cta_label="Ver comando de carga",
        cta_cb=lambda: st.code(
            "python -m scheduler.run_update --backfill 2024 1"
        ),
    )
    st.stop()
# ── Inicializar filtros desde URL params (sólo en la primera carga) ──────────────
if "_qp_loaded" not in st.session_state:
    init_filters = FiltersState.from_query_params(dict(st.query_params))
    if init_filters.q:
        st.session_state["fs_q"] = init_filters.q
    if init_filters.estados:
        valid_estados = set(df_full["estado_desc"].dropna().unique())
        st.session_state["fs_estados"] = [e for e in init_filters.estados if e in valid_estados]
    if init_filters.ccaas:
        valid_ccaas = set(df_full["ccaa"].dropna().unique())
        st.session_state["fs_ccaas"] = [c for c in init_filters.ccaas if c in valid_ccaas]
    if init_filters.organos:
        valid_organos = set(df_full["organo_contratacion"].dropna().unique())
        st.session_state["fs_organos"] = [o for o in init_filters.organos if o in valid_organos]
    if init_filters.tipos_proy:
        valid_tipos = set(df_full["tipo_proyecto"].dropna().unique())
        st.session_state["fs_tipos"] = [t for t in init_filters.tipos_proy if t in valid_tipos]
    if init_filters.importe_min > 0:
        st.session_state["fs_imp_min"] = init_filters.importe_min
    if init_filters.rango:
        st.session_state["fs_rango"] = init_filters.rango
    st.session_state["_qp_loaded"] = True
# ── Sidebar: navegación + filtros ─────────────────────────────────────────
with st.sidebar:
    render_sidebar_brand()
    section = st.radio(
        "nav",
        list(SECTIONS.keys()),
        label_visibility="collapsed",
        key="nav_section",
    )
    st.divider()
    filters: FiltersState = render_sidebar_filters(df_full)
    st.divider()
    compact = st.toggle("Modo compacto", key="density_compact", value=False)

# ── Inyectar override de densidad compacta ────────────────────────────────
if compact:
    st.markdown(COMPACT_DENSITY_CSS, unsafe_allow_html=True)
# ── Aplicar filtros ─────────────────────────────────────────────────────
df = apply_filters(df_full, filters)
# ── Sincronizar filtros activos → URL (compartible) ────────────────────────
new_qp = filters.to_query_params()
cur_qp = dict(st.query_params)
if cur_qp != new_qp:
    for key in list(cur_qp):
        if key not in new_qp:
            del st.query_params[key]
    st.query_params.update(new_qp)
# ── KPI cards ───────────────────────────────────────────────────────────
render_kpi_bar(df)

st.markdown("")

# ── Sub-nav + breadcrumb ───────────────────────────────────────────────────
_pages = SECTIONS[section]
page = sub_nav(_pages, key=f"nav_page_{section}")
breadcrumb(section, page)
active_filters_chips(filters)
st.markdown("")

# ── Page router ────────────────────────────────────────────────────────────
ctx = PageContext(
    df=df,
    df_full=df_full,
    filters=filters,
    tokens=TOKENS,
    plotly_template=PLOTLY_TEMPLATE,
    color_sequence=COLOR_SEQUENCE,
)
PAGE_REGISTRY[page](ctx)

# ── Footer ─────────────────────────────────────────────────────────────
