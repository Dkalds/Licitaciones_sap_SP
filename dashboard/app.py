"""Dashboard Streamlit — Licitaciones SAP del Sector Público."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.auth import check_password
from dashboard.components.kpi import kpi_card
from dashboard.components.layout import (render_footer, render_header,
                                          render_sidebar_brand)
from dashboard.components.navigation import (active_filters_chips, breadcrumb,
                                              sub_nav)
from dashboard.components.states import empty_state
from dashboard.data_loader import load_dataframe
from dashboard.filters import FiltersState, apply_filters, render_sidebar_filters
from dashboard.pages import PAGE_REGISTRY
from dashboard.pages._base import PageContext
from dashboard.theme import (COMPACT_DENSITY_CSS, TOKENS, build_css,
                              get_color_sequence, register_plotly_template)
from dashboard.utils.format import fmt_eur

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

# ── Section navigation ─────────────────────────────────────────────────
SECTIONS = {
    "Vista General": ["Resumen", "Tendencias", "Detalle"],
    "Mercado": ["Órganos", "Geografía", "Proyectos & Módulos"],
    "Competencia": ["Competidores", "Pipeline & Alertas"],
}
SECTION_ICONS = {"Vista General": "◈", "Mercado": "◉",
                 "Competencia": "◆"}

# ── Header ──────────────────────────────────────────────────────────────
render_header()

df_full = load_dataframe()

if df_full.empty:
    empty_state(
        "📭",
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
        "nav", list(SECTIONS.keys()),
        format_func=lambda x: f"{SECTION_ICONS[x]}  {x}",
        label_visibility="collapsed", key="nav_section",
    )
    st.divider()
    filters: FiltersState = render_sidebar_filters(df_full)
    st.divider()
    compact = st.toggle("📰 Modo compacto", key="density_compact", value=False)

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
total = len(df)
importe_total = df["importe"].sum(skipna=True)
importe_medio = df["importe"].mean(skipna=True) or 0
n_organos = df["organo_contratacion"].nunique()
n_ccaa = df["ccaa"].nunique()

hoy = pd.Timestamp.now("UTC")
ult30 = df[df["fecha_publicacion"] >= (hoy - pd.Timedelta(days=30))]
prev30 = df[(df["fecha_publicacion"] < (hoy - pd.Timedelta(days=30))) &
            (df["fecha_publicacion"] >= (hoy - pd.Timedelta(days=60)))]
delta_n = len(ult30) - len(prev30)
delta_pct = (delta_n / len(prev30) * 100) if len(prev30) else 0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(kpi_card("Licitaciones SAP", f"{total:,}",
                          icon="📋"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Importe total", fmt_eur(importe_total),
                          icon="💰"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Importe medio", fmt_eur(importe_medio),
                          icon="📈"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Órganos distintos", f"{n_organos}",
                          icon="🏛️"), unsafe_allow_html=True)
with c5:
    delta_txt = (f"{delta_pct:+.0f}% últ. 30d" if prev30.shape[0]
                  else "sin comparativa")
    st.markdown(kpi_card("CCAA cubiertas", f"{n_ccaa}/17",
                          delta=delta_txt,
                          delta_up=delta_n >= 0, icon="🗺️"),
                 unsafe_allow_html=True)

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
