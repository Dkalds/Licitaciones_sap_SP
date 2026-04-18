"""Dashboard Streamlit — Licitaciones SAP del Sector Público."""
from __future__ import annotations

import html
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hmac

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from config import DASHBOARD_PASSWORD
from dashboard.data_loader import (load_adjudicaciones, load_dataframe,
                                     load_extracciones)
from dashboard.forecast import build_forecast_df

# ── Config & estilo ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Licitaciones SAP · Sector Público",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  }
  .block-container { padding-top: 3.5rem; padding-bottom: 2rem; max-width: 1440px; }
  h1, h2, h3, h4 {
    font-weight: 600 !important; letter-spacing: -0.025em;
    font-family: 'Inter', sans-serif !important;
    color: #E8E8E8 !important;
  }
  h1 { font-size: 1.35rem !important; }
  h2 { font-size: 1.1rem !important; color: #B0B0B0 !important; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    width: 260px !important; min-width: 260px !important; max-width: 260px !important;
    background: linear-gradient(180deg, #0D0D0D 0%, #111111 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
  }
  section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }

  /* KPI Cards — dark corporate */
  .kpi-card {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    transition: border-color 0.2s, transform 0.15s;
  }
  .kpi-card:hover { border-color: #86BC25; transform: translateY(-1px); }
  .kpi-card .label {
    color: #808080; font-size: 0.7rem; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px;
  }
  .kpi-card .value {
    color: #F0F0F0; font-size: 1.7rem; font-weight: 700;
    line-height: 1.1; letter-spacing: -0.02em;
  }
  .kpi-card .delta { font-size: 0.76rem; margin-top: 6px; font-weight: 500; }
  .kpi-card .delta.up { color: #86BC25; }
  .kpi-card .delta.down { color: #E21836; }
  .kpi-card .icon { font-size: 1rem; opacity: 0.35; float: right; }

  /* Top cards */
  .top-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.05);
    border-left: 3px solid #86BC25;
    border-radius: 12px; padding: 14px 18px; margin-bottom: 8px;
    transition: border-color 0.15s;
  }
  .top-card:hover { border-color: rgba(255,255,255,0.12); border-left-color: #6B9B1E; }
  .top-card .amount { font-size: 1.25rem; font-weight: 700; color: #86BC25; letter-spacing: -0.01em; }
  .top-card .title { font-size: 0.88rem; color: #E0E0E0; margin: 4px 0; line-height: 1.35; }
  .top-card .meta { font-size: 0.74rem; color: #808080; }

  /* Breadcrumb */
  .bc { font-size: 0.8rem; margin-bottom: 2px; }
  .bc-section { color: #808080; font-weight: 500; }
  .bc-sep { color: #555555; margin: 0 4px; }
  .bc-page { color: #86BC25; font-weight: 500; }

  /* Metrics & misc */
  div[data-testid="stMetricValue"] { font-size: 1.5rem; }
  .stDivider { opacity: 0.3; }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ── Autenticación ────────────────────────────────────────────────────────
def _get_password() -> str:
    """Lee la contraseña desde st.secrets (Cloud) o config.py (.env / local)."""
    try:
        return st.secrets.get("DASHBOARD_PASSWORD", "") or DASHBOARD_PASSWORD
    except FileNotFoundError:
        return DASHBOARD_PASSWORD


def _check_password() -> bool:
    """Muestra login y devuelve True si está autenticado o no hay password."""
    password = _get_password()
    if not password:
        return True
    if st.session_state.get("authenticated"):
        return True

    st.markdown("### 🔒 Acceso restringido")
    pwd = st.text_input("Contraseña", type="password", key="login_pwd")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(pwd, password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()


_check_password()

# ── Plotly premium template ─────────────────────────────────────────────
_premium = go.Layout(
    font=dict(family="Inter, -apple-system, sans-serif", color="#A0A0A0", size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False, zeroline=False,
               linecolor="rgba(255,255,255,0.08)", linewidth=1,
               tickfont=dict(size=11, color="#808080")),
    yaxis=dict(showgrid=False, zeroline=False,
               linecolor="rgba(255,255,255,0.08)", linewidth=1,
               tickfont=dict(size=11, color="#808080")),
    colorway=["#86BC25", "#00A3E0", "#A0A0A0", "#D0D0D0",
              "#6B9B1E", "#0083B3", "#E0E0E0", "#66BB6A"],
    hoverlabel=dict(bgcolor="#1A1A1A", bordercolor="rgba(255,255,255,0.1)",
                    font=dict(family="Inter", size=12, color="#E0E0E0")),
    legend=dict(font=dict(size=11, color="#A0A0A0")),
)
pio.templates["premium_dark"] = go.layout.Template(layout=_premium)
PLOTLY_TEMPLATE = "plotly_dark+premium_dark"
COLOR_SEQUENCE = ["#86BC25", "#00A3E0", "#A0A0A0", "#D0D0D0",
                  "#6B9B1E", "#0083B3", "#E0E0E0", "#66BB6A"]

# ── Section navigation ─────────────────────────────────────────────────
SECTIONS = {
    "Vista General": ["Resumen", "Tendencias", "Detalle"],
    "Mercado": ["Órganos", "Geografía", "Proyectos & Módulos"],
    "Competencia": ["Competidores", "Pipeline & Alertas"],
}
SECTION_ICONS = {"Vista General": "◈", "Mercado": "◉",
                 "Competencia": "◆"}

# ── Helpers ─────────────────────────────────────────────────────────────
def fmt_eur(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "—"
    if abs(x) >= 1e9:
        return f"{x/1e9:.2f} B€"
    if abs(x) >= 1e6:
        return f"{x/1e6:.2f} M€"
    if abs(x) >= 1e3:
        return f"{x/1e3:.1f} k€"
    return f"{x:,.0f} €"


def kpi_card(label: str, value: str, delta: str | None = None,
             delta_up: bool = True, icon: str = "") -> str:
    delta_html = ""
    if delta:
        cls = "up" if delta_up else "down"
        arrow = "▲" if delta_up else "▼"
        delta_html = f'<div class="delta {cls}">{arrow} {delta}</div>'
    return (f'<div class="kpi-card"><span class="icon">{icon}</span>'
            f'<div class="label">{label}</div>'
            f'<div class="value">{value}</div>{delta_html}</div>')


def safe_url(url: str | None) -> str:
    """Valida que la URL use un esquema seguro. Previene javascript: URIs."""
    if not url or not isinstance(url, str):
        return "#"
    stripped = url.strip()
    if stripped.lower().startswith(("http://", "https://")):
        return stripped
    return "#"


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    out = BytesIO()
    cols = [c for c in df.columns if c not in ("modulos",)]
    export = df[cols].copy()
    # Excel no soporta tz-aware datetimes
    for c in export.select_dtypes(include=["datetimetz"]).columns:
        export[c] = export[c].dt.tz_localize(None)
    export.to_excel(out, index=False, sheet_name="Licitaciones SAP")
    return out.getvalue()


# ── Header ──────────────────────────────────────────────────────────────
_hdr_l, _hdr_r = st.columns([9, 1])
with _hdr_l:
    st.markdown("## Licitaciones SAP · Sector Público")
with _hdr_r:
    if st.button("↻", use_container_width=True, help="Refrescar caché"):
        st.cache_data.clear()
        st.rerun()

df_full = load_dataframe()

if df_full.empty:
    st.warning("No hay datos en la BD. Ejecuta:")
    st.code("python -m scheduler.run_update --backfill 2024 1")
    st.stop()

# ── Sidebar: navegación + filtros ─────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<p style="font-size:1.05rem;font-weight:600;letter-spacing:-0.02em;'
        'color:#E0E0E0;margin:0 0 1rem 2px">⬡ Licitaciones SAP</p>',
        unsafe_allow_html=True,
    )
    section = st.radio(
        "nav", list(SECTIONS.keys()),
        format_func=lambda x: f"{SECTION_ICONS[x]}  {x}",
        label_visibility="collapsed", key="nav_section",
    )
    st.divider()
    st.markdown("##### Filtros")

    # Búsqueda libre
    q = st.text_input("🔍 Buscar (título / descripción)", "")

    # Rango fechas
    fmin = df_full["fecha_publicacion"].min()
    fmax = df_full["fecha_publicacion"].max()
    if pd.notna(fmin) and pd.notna(fmax):
        rango = st.date_input(
            "Rango fechas", (fmin.date(), fmax.date()),
            min_value=fmin.date(), max_value=fmax.date(),
        )
    else:
        rango = None

    estados = st.multiselect(
        "Estado",
        sorted(df_full["estado_desc"].dropna().unique()),
    )
    ccaas = st.multiselect(
        "Comunidad Autónoma",
        sorted(df_full["ccaa"].dropna().unique()),
    )
    organos_opts = sorted(df_full["organo_contratacion"].dropna().unique())
    organos = st.multiselect("Órgano contratante", organos_opts)

    tipos_proy = st.multiselect(
        "Tipo de proyecto",
        sorted(df_full["tipo_proyecto"].dropna().unique()),
    )

    importe_min = st.number_input("Importe mínimo (€)", min_value=0,
                                   value=0, step=10000)

    st.divider()
    st.caption(f"Última actualización BD:\n"
               f"{df_full['fecha_extraccion'].max()}")

# ── Aplicar filtros ─────────────────────────────────────────────────────
df = df_full.copy()
if q:
    mask = (df["titulo"].str.contains(q, case=False, na=False) |
            df["descripcion"].str.contains(q, case=False, na=False))
    df = df[mask]
if rango and isinstance(rango, tuple) and len(rango) == 2:
    df = df[(df["fecha_publicacion"].dt.date >= rango[0]) &
            (df["fecha_publicacion"].dt.date <= rango[1])]
if estados:
    df = df[df["estado_desc"].isin(estados)]
if ccaas:
    df = df[df["ccaa"].isin(ccaas)]
if organos:
    df = df[df["organo_contratacion"].isin(organos)]
if tipos_proy:
    df = df[df["tipo_proyecto"].isin(tipos_proy)]
if importe_min > 0:
    df = df[df["importe"].fillna(0) >= importe_min]

# ── KPI cards ───────────────────────────────────────────────────────────
total = len(df)
importe_total = df["importe"].sum(skipna=True)
importe_medio = df["importe"].mean(skipna=True) or 0
n_organos = df["organo_contratacion"].nunique()
n_ccaa = df["ccaa"].nunique()

# YoY comparison: comparar últimos 30 días vs 30 días anteriores
hoy = pd.Timestamp.utcnow()
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

st.markdown("")  # espaciado

# ── Sub-nav + breadcrumb ───────────────────────────────────────────────────
_pages = SECTIONS[section]
page = st.radio("p", _pages, horizontal=True,
                label_visibility="collapsed",
                key=f"nav_page_{section}")
st.markdown(
    f'<div class="bc"><span class="bc-section">{section}</span>'
    f'<span class="bc-sep">›</span>'
    f'<span class="bc-page">{page}</span></div>',
    unsafe_allow_html=True,
)
st.markdown("")

# ─── Tab Resumen ────────────────────────────────────────────────────────
if page == "Resumen":
    cL, cR = st.columns([2, 1])
    with cL:
        st.subheader("Top 10 licitaciones por importe")
        top = (df.dropna(subset=["importe"])
                 .nlargest(10, "importe"))
        for _, row in top.iterrows():
            url = safe_url(row.get("url"))
            titulo = html.escape(str(row["titulo"])[:120])
            organo = html.escape(str(row.get("organo_contratacion") or "—"))
            estado = html.escape(str(row.get("estado_desc") or "—"))
            tipo = html.escape(str(row.get("tipo_proyecto") or "—"))
            modulos = html.escape(str(row.get("modulos_str") or "—"))
            st.markdown(
                f'<div class="top-card">'
                f'<div class="amount">{fmt_eur(row["importe"])}</div>'
                f'<div class="title"><a href="{url}" target="_blank" '
                f'style="color:#E0E0E0;text-decoration:none">'
                f'{titulo}</a></div>'
                f'<div class="meta">'
                f'{organo} · '
                f'{estado} · '
                f'{tipo} · '
                f'<b>{modulos}</b></div></div>',
                unsafe_allow_html=True,
            )
    with cR:
        st.subheader("Distribución por estado")
        est = (df.groupby("estado_desc").size()
                  .reset_index(name="n")
                  .sort_values("n", ascending=False))
        if not est.empty:
            fig = px.pie(est, names="estado_desc", values="n", hole=0.55,
                          template=PLOTLY_TEMPLATE,
                          color_discrete_sequence=COLOR_SEQUENCE)
            fig.update_traces(textposition="outside", textinfo="label+percent")
            fig.update_layout(showlegend=False, height=320,
                               margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tipos de proyecto")
        tp = (df.groupby("tipo_proyecto").size()
                .reset_index(name="n").sort_values("n", ascending=True))
        if not tp.empty:
            fig = px.bar(tp, x="n", y="tipo_proyecto", orientation="h",
                          template=PLOTLY_TEMPLATE,
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

# ─── Tab Tendencias ─────────────────────────────────────────────────────
if page == "Tendencias":
    st.subheader("Evolución mensual")
    g = (df.dropna(subset=["mes"])
           .groupby("mes")
           .agg(n=("id_externo", "count"),
                importe=("importe", "sum"))
           .reset_index())

    if g.empty:
        st.info("Sin datos suficientes")
    else:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(g, x="mes", y="n", template=PLOTLY_TEMPLATE,
                          labels={"mes": "Mes", "n": "Nº licitaciones"},
                          color_discrete_sequence=["#86BC25"])
            fig.update_layout(height=380,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.area(g, x="mes", y="importe", template=PLOTLY_TEMPLATE,
                           labels={"mes": "Mes", "importe": "Importe (€)"},
                           color_discrete_sequence=["#00A3E0"])
            fig.update_layout(height=380,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Heatmap mes × estado")
    if not df.empty and df["mes"].notna().any():
        hm = (df.dropna(subset=["mes"])
                .groupby([df["mes"].dt.strftime("%Y-%m"),
                          "estado_desc"]).size()
                .reset_index(name="n"))
        hm.columns = ["mes", "estado", "n"]
        pivot = hm.pivot(index="estado", columns="mes",
                          values="n").fillna(0)
        fig = px.imshow(pivot, aspect="auto", template=PLOTLY_TEMPLATE,
                         color_continuous_scale="Greens",
                         labels=dict(color="Licitaciones"))
        fig.update_layout(height=350,
                           margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Distribución de importes (escala log)")
    if df["importe"].notna().any():
        fig = px.histogram(
            df.dropna(subset=["importe"]).assign(
                importe_log=lambda x: x["importe"].clip(lower=1)),
            x="importe_log", log_x=True, nbins=40,
            template=PLOTLY_TEMPLATE,
            color_discrete_sequence=["#86BC25"],
            labels={"importe_log": "Importe (€, log)"})
        fig.update_layout(height=320,
                           margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

# ─── Tab Órganos ────────────────────────────────────────────────────────
if page == "Órganos":
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
                          template=PLOTLY_TEMPLATE,
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
                          template=PLOTLY_TEMPLATE,
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
            values="importe", template=PLOTLY_TEMPLATE,
            color="importe", color_continuous_scale="Greens")
        fig.update_layout(height=600,
                           margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

# ─── Tab Geografía ──────────────────────────────────────────────────────
if page == "Geografía":
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
                          orientation="h", template=PLOTLY_TEMPLATE,
                          color="importe", color_continuous_scale="Greens",
                          labels={"n": "Licitaciones", "ccaa": "",
                                  "importe": "Importe €"})
            fig.update_layout(height=600,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no hay datos geográficos. Re-ejecuta el pipeline "
                     "tras la actualización del parser.")

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
            st.dataframe(
                prov.rename(columns={"n": "Lic.",
                                       "importe": "Importe €"}),
                use_container_width=True, hide_index=True,
                column_config={
                    "Importe €": st.column_config.NumberColumn(
                        format="%.0f €")},
            )

# ─── Tab Proyectos & módulos ───────────────────────────────────────────
if page == "Proyectos & Módulos":
    cMod, cType = st.columns(2)

    with cMod:
        st.subheader("Módulos / productos SAP detectados")
        # Explode módulos (cada licitación puede tener varios)
        mod_df = df.explode("modulos")
        mod_count = (mod_df.groupby("modulos")
                       .agg(n=("id_externo", "count"),
                            importe=("importe", "sum"))
                       .reset_index()
                       .sort_values("n", ascending=False))
        if not mod_count.empty:
            fig = px.bar(mod_count.head(15).sort_values("n"),
                          x="n", y="modulos", orientation="h",
                          template=PLOTLY_TEMPLATE,
                          color="importe",
                          color_continuous_scale="YlGn",
                          labels={"n": "Apariciones", "modulos": "",
                                  "importe": "Importe €"})
            fig.update_layout(height=520,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    with cType:
        st.subheader("Tipo de proyecto × Estado")
        cross = (df.groupby(["tipo_proyecto", "estado_desc"])
                   .size().reset_index(name="n"))
        if not cross.empty:
            fig = px.sunburst(cross, path=["tipo_proyecto", "estado_desc"],
                                values="n", template=PLOTLY_TEMPLATE,
                                color="n", color_continuous_scale="Greens")
            fig.update_layout(height=520,
                                margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top códigos CPV")
    cpv_df = (df.groupby(["cpv", "cpv_desc"])
                .agg(n=("id_externo", "count"),
                     importe=("importe", "sum"))
                .reset_index()
                .sort_values("n", ascending=False)
                .head(15))
    if not cpv_df.empty:
        st.dataframe(
            cpv_df.rename(columns={
                "cpv_desc": "CPV", "n": "Lic.", "importe": "Importe €"})
                  [["CPV", "Lic.", "Importe €"]],
            use_container_width=True, hide_index=True,
            column_config={
                "Importe €": st.column_config.NumberColumn(format="%.0f €")},
        )

# ─── Tab Detalle ────────────────────────────────────────────────────────
if page == "Detalle":
    st.subheader(f"Detalle de licitaciones ({len(df)})")
    st.caption("Plataforma de Contratación del Sector Público — "
               "reutilización al amparo de la Ley 37/2007")

    cdl1, cdl2 = st.columns([1, 6])
    with cdl1:
        st.download_button(
            "⬇️ Excel",
            data=to_excel_bytes(df),
            file_name="licitaciones_sap.xlsx",
            mime="application/vnd.openxmlformats-officedocument."
                 "spreadsheetml.sheet",
            use_container_width=True,
        )
    with cdl2:
        st.download_button(
            "⬇️ CSV",
            data=df.drop(columns=["modulos"]).to_csv(index=False)
                   .encode("utf-8-sig"),
            file_name="licitaciones_sap.csv", mime="text/csv",
        )

    cols = ["fecha_publicacion", "titulo", "organo_contratacion",
             "ccaa", "importe", "moneda", "estado_desc",
             "tipo_proyecto", "modulos_str", "cpv_desc", "url"]
    cols = [c for c in cols if c in df.columns]
    show = df[cols].sort_values("fecha_publicacion", ascending=False)

    st.dataframe(
        show, use_container_width=True, hide_index=True,
        column_config={
            "fecha_publicacion": st.column_config.DatetimeColumn(
                "Fecha", format="DD-MM-YYYY"),
            "titulo": st.column_config.TextColumn("Título", width="large"),
            "organo_contratacion": st.column_config.TextColumn(
                "Órgano", width="medium"),
            "ccaa": st.column_config.TextColumn("CCAA", width="small"),
            "importe": st.column_config.NumberColumn(
                "Importe", format="%.0f €"),
            "estado_desc": st.column_config.TextColumn("Estado"),
            "tipo_proyecto": st.column_config.TextColumn("Tipo"),
            "modulos_str": st.column_config.TextColumn("Módulos"),
            "cpv_desc": st.column_config.TextColumn("CPV"),
            "url": st.column_config.LinkColumn("Enlace", display_text="🔗"),
        },
        height=600,
    )

    st.divider()
    st.subheader("🔎 Vista expandida (clic para ver descripción completa)")
    for _, row in df.sort_values("fecha_publicacion",
                                   ascending=False).head(20).iterrows():
        with st.expander(
            f"💼 {fmt_eur(row['importe'])} — {row['titulo'][:90]}"
        ):
            cE1, cE2 = st.columns([2, 1])
            with cE1:
                st.markdown(f"**Órgano:** {row.get('organo_contratacion','—')}")
                st.markdown(f"**Estado:** {row.get('estado_desc','—')} · "
                            f"**Tipo proyecto:** {row.get('tipo_proyecto','—')}")
                st.markdown(f"**Módulos SAP detectados:** "
                            f"{row.get('modulos_str','—')}")
                st.markdown(f"**CPV:** {row.get('cpv_desc','—')}")
                st.markdown(f"**Provincia / CCAA:** "
                            f"{row.get('provincia','—')} · "
                            f"{row.get('ccaa','—')}")
                st.markdown("**Descripción:**")
                st.write(row.get("descripcion") or "—")
            with cE2:
                st.metric("Importe", fmt_eur(row["importe"]))
                if row.get("url"):
                    st.link_button("📄 Ver licitación oficial",
                                    row["url"], use_container_width=True)

# ─── Competidores ─────────────────────────────────────────────────────────
if page == "Competidores":
    st.subheader("Análisis de competidores")
    st.caption("Posicionamiento, dominio de mercado, especialización y búsqueda por empresa.")

    adj_ci = load_adjudicaciones()
    if adj_ci.empty:
        st.info("Sin datos de adjudicación disponibles.")
    else:
        # Restringir al filtro activo del sidebar
        ids_ci = set(df["id_externo"])
        adj_ci = adj_ci[adj_ci["licitacion_id"].isin(ids_ci)].copy()

        if adj_ci.empty:
            st.info("Sin adjudicaciones para los filtros activos.")
        else:
            # ── Selector de empresa ──────────────────────────────────────
            top_empresas = (adj_ci.groupby("empresa_key", dropna=True)
                              .agg(nombre=("nombre_canonico", "first"),
                                   importe=("importe_adjudicado", "sum"))
                              .sort_values("importe", ascending=False)
                              .head(200))
            opciones_ci = top_empresas["nombre"].tolist()
            sel_empresas = st.multiselect(
                "Selecciona una o varias empresas a analizar",
                opciones_ci,
                placeholder="Empieza a escribir…",
                key="ci_empresas",
            )
            if not sel_empresas:
                sel_empresas = opciones_ci[:5]  # top 5 por defecto
                st.caption(f"Mostrando top 5 por defecto.")

            keys_ci = top_empresas[
                top_empresas["nombre"].isin(sel_empresas)].index.tolist()
            sub_ci = adj_ci[adj_ci["empresa_key"].isin(keys_ci)].copy()
            total_mercado = adj_ci["importe_adjudicado"].sum(skipna=True)

            # ── KPIs por empresa ────────────────────────────────────────
            metr_ci = (sub_ci.groupby("empresa_key", dropna=True)
                         .agg(empresa=("nombre_canonico", "first"),
                              contratos=("id", "count"),
                              volumen=("importe_adjudicado", "sum"),
                              ticket_medio=("importe_adjudicado", "mean"),
                              organos=("organo_contratacion", "nunique"))
                         .reset_index(drop=True))
            metr_ci["cuota_pct"] = (
                metr_ci["volumen"] / total_mercado * 100
                if total_mercado else 0)
            # Tasa de dependencia de cliente principal
            def _dep_cliente(key: str) -> float:
                s = sub_ci[sub_ci["empresa_key"] == key]["organo_contratacion"]
                if s.empty:
                    return 0.0
                return float(s.value_counts(normalize=True).iloc[0] * 100)

            metr_ci["dep_cliente_pct"] = [
                _dep_cliente(k) for k in
                sub_ci.groupby("empresa_key").groups.keys()
                if k in top_empresas.index
            ][:len(metr_ci)]

            st.markdown("##### KPIs de posición y dominio")
            kci_cols = st.columns(len(metr_ci) if len(metr_ci) <= 5 else 5)
            for i, (_, row_m) in enumerate(metr_ci.iterrows()):
                col_i = kci_cols[i % len(kci_cols)]
                with col_i:
                    st.markdown(
                        kpi_card(row_m["empresa"][:22],
                                 fmt_eur(row_m["volumen"]),
                                 delta=f"{row_m['cuota_pct']:.1f}% cuota · "
                                       f"{row_m['contratos']} contratos",
                                 delta_up=True, icon="🏢"),
                        unsafe_allow_html=True,
                    )

            st.markdown("")

            # ── Volumen + cuota de mercado ───────────────────────────────
            cCI1, cCI2 = st.columns(2)
            with cCI1:
                st.subheader("Volumen adjudicado y cuota de mercado")
                fig = px.bar(metr_ci.sort_values("volumen"),
                             x="volumen", y="empresa", orientation="h",
                             template=PLOTLY_TEMPLATE,
                             color="cuota_pct",
                             color_continuous_scale="Greens",
                             labels={"volumen": "Importe €",
                                     "empresa": "",
                                     "cuota_pct": "Cuota %"},
                             hover_data=["contratos", "cuota_pct"])
                fig.update_layout(height=360,
                                  margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

            with cCI2:
                st.subheader("Ticket medio vs Dependencia de cliente")
                if not metr_ci.empty and "dep_cliente_pct" in metr_ci.columns:
                    fig = px.scatter(
                        metr_ci, x="ticket_medio", y="dep_cliente_pct",
                        size="contratos", color="cuota_pct",
                        hover_name="empresa",
                        template=PLOTLY_TEMPLATE,
                        color_continuous_scale="RdYlGn_r",
                        labels={"ticket_medio": "Ticket medio (€)",
                                "dep_cliente_pct": "Dependencia cliente (%)",
                                "cuota_pct": "Cuota %",
                                "contratos": "Nº contratos"},
                        log_x=True)
                    fig.update_layout(height=360,
                                      margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Arriba-izquierda = tickets pequeños + cliente cautivo. "
                               "Abajo-derecha = alta diversificación.")

            # ── Mapa de calor geográfico ─────────────────────────────────
            st.subheader("Distribución geográfica por CCAA")
            geo_ci = (sub_ci.dropna(subset=["ccaa"])
                       .groupby(["nombre_canonico", "ccaa"])
                       .agg(importe=("importe_adjudicado", "sum"))
                       .reset_index())
            if not geo_ci.empty:
                fig = px.density_heatmap(
                    geo_ci, x="ccaa", y="nombre_canonico",
                    z="importe", histfunc="sum",
                    template=PLOTLY_TEMPLATE,
                    color_continuous_scale="Greens",
                    labels={"ccaa": "CCAA",
                            "nombre_canonico": "Empresa",
                            "importe": "Importe €"})
                fig.update_layout(height=max(280, len(sel_empresas) * 60),
                                  margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

            # ── Treemap de especialización CPV ───────────────────────────
            st.subheader("Especialización por CPV")
            cpv_ci = sub_ci.merge(
                df[["id_externo", "cpv_desc"]].drop_duplicates(),
                left_on="licitacion_id", right_on="id_externo", how="left")
            cpv_ci = cpv_ci.dropna(subset=["cpv_desc", "importe_adjudicado"])
            if not cpv_ci.empty:
                fig = px.treemap(
                    cpv_ci, path=["nombre_canonico", "cpv_desc"],
                    values="importe_adjudicado",
                    template=PLOTLY_TEMPLATE,
                    color="importe_adjudicado",
                    color_continuous_scale="Greens",
                    labels={"importe_adjudicado": "Importe €"})
                fig.update_layout(height=480,
                                  margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

            # ── Estacionalidad ───────────────────────────────────────────
            st.subheader("Estacionalidad de adjudicaciones")
            seas_ci = sub_ci.dropna(subset=["fecha_adjudicacion"]).copy()
            if not seas_ci.empty:
                seas_ci["mes"] = (seas_ci["fecha_adjudicacion"]
                                   .dt.to_period("M").dt.to_timestamp())
                seas_g = (seas_ci.groupby(["mes", "nombre_canonico"])
                            .agg(importe=("importe_adjudicado", "sum"),
                                 n=("id", "count"))
                            .reset_index())
                fig = px.line(
                    seas_g, x="mes", y="importe",
                    color="nombre_canonico", markers=True,
                    template=PLOTLY_TEMPLATE,
                    color_discrete_sequence=COLOR_SEQUENCE,
                    labels={"mes": "", "importe": "Importe adjudicado (€)",
                            "nombre_canonico": "Empresa"})
                fig.update_layout(height=360,
                                  margin=dict(t=10, b=10, l=10, r=10),
                                  legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)

            # ── Análisis de nicho (keywords frecuentes) ──────────────────
            st.subheader("Perfil de nicho — palabras clave más frecuentes")
            st.caption("Extraídas de los títulos y descripciones de sus contratos.")
            import re as _re
            from collections import Counter

            _STOPWORDS = {
                "de", "del", "la", "el", "los", "las", "para", "por",
                "en", "con", "y", "a", "e", "o", "un", "una", "se",
                "su", "al", "que", "es", "no", "lo", "le", "como",
                "una", "sus", "más", "este", "esta", "estos",
                "servicio", "servicios", "contrato", "lote",
            }
            nicho_cols = st.columns(min(len(sel_empresas), 3))
            for col_idx, emp_name in enumerate(sel_empresas[:3]):
                key_emp = top_empresas[
                    top_empresas["nombre"] == emp_name].index
                if len(key_emp) == 0:
                    continue
                rows_emp = sub_ci[sub_ci["empresa_key"] == key_emp[0]]
                lic_ids = set(rows_emp["licitacion_id"])
                textos = df[df["id_externo"].isin(lic_ids)].apply(
                    lambda r: f"{r.get('titulo','')} {r.get('descripcion','')}",
                    axis=1)
                words = _re.findall(r"\b[a-záéíóúüñ]{4,}\b",
                                    " ".join(textos.dropna()).lower())
                top_words = Counter(
                    w for w in words if w not in _STOPWORDS
                ).most_common(12)
                with nicho_cols[col_idx]:
                    st.markdown(f"**{emp_name[:30]}**")
                    if top_words:
                        wdf = pd.DataFrame(top_words,
                                           columns=["palabra", "frecuencia"])
                        fig = px.bar(wdf, x="frecuencia", y="palabra",
                                     orientation="h",
                                     template=PLOTLY_TEMPLATE,
                                     color="frecuencia",
                                     color_continuous_scale="Greys",
                                     labels={"frecuencia": "",
                                             "palabra": ""})
                        fig.update_layout(
                            height=320, showlegend=False,
                            coloraxis_showscale=False,
                            margin=dict(t=5, b=5, l=5, r=5))
                        st.plotly_chart(fig, use_container_width=True)

            # ── Métricas comparativas por empresa ──────────────────────────
            st.divider()
            st.subheader("Métricas comparativas por empresa")
            st.caption("Solo empresas con al menos 2 adjudicaciones.")

            def _pct_top_organo(s: pd.Series) -> float:
                if s.empty:
                    return 0.0
                counts = s.value_counts(normalize=True)
                return float(counts.iloc[0] * 100)

            adj_m = adj_ci.copy()
            adj_m["es_monopolio"] = (adj_m["n_ofertas_recibidas"] == 1).astype(int)

            metr = (adj_m.groupby("empresa_key", dropna=False)
                           .agg(empresa=("nombre_canonico", "first"),
                                nif=("nif_norm", "first"),
                                contratos=("id", "count"),
                                importe_total=("importe_adjudicado", "sum"),
                                importe_medio=("importe_adjudicado", "mean"),
                                baja_media=("baja_pct", "mean"),
                                ofertas_medias=("n_ofertas_recibidas", "mean"),
                                pct_monopolio=("es_monopolio",
                                                lambda s: s.mean() * 100),
                                organos=("organo_contratacion", "nunique"),
                                pct_top_organo=("organo_contratacion",
                                                  _pct_top_organo),
                                primera=("fecha_adjudicacion", "min"),
                                ultima=("fecha_adjudicacion", "max"))
                           .reset_index(drop=True))
            metr = metr[metr["contratos"] >= 2].copy()
            if not metr.empty:
                antig_dias = (metr["ultima"] - metr["primera"]).dt.days
                antig_años = (antig_dias / 365.25).clip(lower=0.5)
                metr["contratos_año"] = (metr["contratos"] / antig_años).round(1)
                total_imp = metr["importe_total"].sum()
                metr["cuota_pct"] = (
                    metr["importe_total"] / total_imp * 100
                    if total_imp else 0)
                metr = metr.sort_values("importe_total", ascending=False)

                st.dataframe(
                    metr[["empresa", "nif", "contratos", "contratos_año",
                          "importe_total", "cuota_pct", "importe_medio",
                          "baja_media", "ofertas_medias", "pct_monopolio",
                          "organos", "pct_top_organo", "ultima"]].head(100),
                    use_container_width=True, hide_index=True, height=380,
                    column_config={
                        "empresa": st.column_config.TextColumn("Empresa",
                                                                 width="large"),
                        "nif": st.column_config.TextColumn("NIF", width="small"),
                        "contratos": st.column_config.NumberColumn("Contratos"),
                        "contratos_año": st.column_config.NumberColumn("Contr./año"),
                        "importe_total": st.column_config.NumberColumn(
                            "Importe total", format="%.0f €"),
                        "cuota_pct": st.column_config.NumberColumn(
                            "Cuota %", format="%.1f%%"),
                        "importe_medio": st.column_config.NumberColumn(
                            "Imp. medio", format="%.0f €"),
                        "baja_media": st.column_config.NumberColumn(
                            "Baja media", format="%.1f%%"),
                        "ofertas_medias": st.column_config.NumberColumn(
                            "Ofertas enfrent.", format="%.1f"),
                        "pct_monopolio": st.column_config.NumberColumn(
                            "% Monopolio", format="%.0f%%"),
                        "organos": st.column_config.NumberColumn("Órganos"),
                        "pct_top_organo": st.column_config.NumberColumn(
                            "% top-1 órgano", format="%.0f%%"),
                        "ultima": st.column_config.DateColumn("Última adj."),
                    },
                )

                # Scatter: posicionamiento competitivo
                st.markdown("##### Mapa de posicionamiento competitivo")
                scatter = metr.dropna(
                    subset=["importe_medio", "baja_media"]).head(60)
                if not scatter.empty:
                    fig = px.scatter(
                        scatter, x="baja_media", y="importe_medio",
                        size="contratos", color="pct_monopolio",
                        hover_name="empresa",
                        template=PLOTLY_TEMPLATE,
                        color_continuous_scale="RdYlGn_r", log_y=True,
                        labels={"baja_media": "Baja media (%) — agresividad",
                                  "importe_medio": "Importe medio (€, log)",
                                  "pct_monopolio": "% monopolio"})
                    fig.update_layout(height=480,
                                       margin=dict(t=20, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Arriba-derecha: contratos grandes + baja agresiva. "
                               "Arriba-izquierda rojo: clientes cautivos.")

            # ── Buscador de empresas ─────────────────────────────────────
            st.divider()
            st.subheader("Buscador de empresas")
            empresa_q = st.text_input(
                "Filtrar por nombre o NIF",
                placeholder="Ej: TELEFONICA, INDRA, B12345678...",
                key="empresa_search",
            )
            ranking = (adj_ci.groupby("empresa_key", dropna=False)
                           .agg(nombre=("nombre_canonico", "first"),
                                nif=("nif_norm", "first"),
                                variantes=("nombre", "nunique"),
                                contratos=("id", "count"),
                                importe_total=("importe_adjudicado", "sum"),
                                organos=("organo_contratacion", "nunique"),
                                ultima=("fecha_adjudicacion", "max"))
                           .reset_index()
                           .sort_values("importe_total", ascending=False))
            if empresa_q:
                mask = (ranking["nombre"].str.contains(
                            empresa_q, case=False, na=False) |
                        ranking["nif"].fillna("").str.contains(
                            empresa_q, case=False, na=False))
                ranking = ranking[mask]

            st.dataframe(
                ranking.drop(columns=["empresa_key"]),
                use_container_width=True, hide_index=True, height=350,
                column_config={
                    "nombre": st.column_config.TextColumn("Empresa",
                                                           width="large"),
                    "nif": st.column_config.TextColumn("NIF/CIF",
                                                        width="small"),
                    "variantes": st.column_config.NumberColumn("Variantes nombre"),
                    "contratos": st.column_config.NumberColumn("Contratos"),
                    "importe_total": st.column_config.NumberColumn(
                        "Importe €", format="%.0f €"),
                    "organos": st.column_config.NumberColumn("Órganos"),
                    "ultima": st.column_config.DateColumn("Última adj."),
                },
            )

            # ── Drill-down por empresa ───────────────────────────────────
            st.divider()
            st.subheader("Drill-down por empresa(s)")
            opciones_df = ranking[["nombre", "empresa_key"]].head(200)
            opciones = opciones_df["nombre"].tolist()
            empresas_sel_dd = st.multiselect(
                "Selecciona una o varias empresas",
                options=opciones,
                placeholder="Empieza a escribir…",
                key="drill_down_empresas",
            )
            if empresas_sel_dd:
                keys_dd = opciones_df[
                    opciones_df["nombre"].isin(empresas_sel_dd)
                ]["empresa_key"].tolist()
                sub_dd = adj_ci[adj_ci["empresa_key"].isin(keys_dd)].copy()

                cE1, cE2, cE3, cE4 = st.columns(4)
                cE1.metric("Empresas", len(empresas_sel_dd))
                cE2.metric("Contratos", len(sub_dd))
                cE3.metric("Importe total",
                            fmt_eur(sub_dd["importe_adjudicado"].sum()))
                cE4.metric("Órganos distintos",
                            sub_dd["organo_contratacion"].nunique())

                if len(empresas_sel_dd) > 1:
                    comp_dd = (sub_dd.groupby("empresa_key")
                                 .agg(nombre=("nombre_canonico", "first"),
                                      contratos=("id", "count"),
                                      importe=("importe_adjudicado", "sum"))
                                 .reset_index(drop=True)
                                 .sort_values("importe", ascending=False))
                    cV1, cV2 = st.columns(2)
                    with cV1:
                        fig = px.bar(comp_dd.sort_values("importe"),
                                      x="importe", y="nombre",
                                      orientation="h",
                                      template=PLOTLY_TEMPLATE,
                                      color="contratos",
                                      color_continuous_scale="YlGn",
                                      labels={"importe": "Importe €",
                                              "nombre": "",
                                              "contratos": "Contratos"})
                        fig.update_layout(height=350,
                                          margin=dict(t=10, b=10, l=10, r=10))
                        st.plotly_chart(fig, use_container_width=True)
                    with cV2:
                        if sub_dd["fecha_adjudicacion"].notna().any():
                            evo = (sub_dd.dropna(subset=["fecha_adjudicacion"])
                                      .assign(mes=lambda x: x["fecha_adjudicacion"]
                                              .dt.to_period("M").dt.to_timestamp())
                                      .groupby(["mes", "nombre_canonico"])
                                      ["importe_adjudicado"].sum()
                                      .reset_index()
                                      .rename(columns={"nombre_canonico": "nombre"}))
                            fig = px.line(evo, x="mes", y="importe_adjudicado",
                                          color="nombre", markers=True,
                                          template=PLOTLY_TEMPLATE,
                                          color_discrete_sequence=COLOR_SEQUENCE,
                                          labels={"mes": "",
                                                  "importe_adjudicado": "Importe €"})
                            fig.update_layout(height=350,
                                              margin=dict(t=10, b=10, l=10, r=10),
                                              legend=dict(orientation="h", y=-0.2))
                            st.plotly_chart(fig, use_container_width=True)

                # Listado de proyectos
                st.markdown("##### Proyectos adjudicados")
                for empresa in empresas_sel_dd:
                    key = opciones_df[
                        opciones_df["nombre"] == empresa]["empresa_key"].iloc[0]
                    emp_proy = sub_dd[sub_dd["empresa_key"] == key]
                    if len(empresas_sel_dd) > 1:
                        st.markdown(f"**{empresa}** "
                                      f"({len(emp_proy)} contratos · "
                                      f"{fmt_eur(emp_proy['importe_adjudicado'].sum())})")
                    for _, row in emp_proy.sort_values(
                            "importe_adjudicado", ascending=False).iterrows():
                        url = row.get("url_lic") or "#"
                        baja = row.get("baja_pct")
                        baja_txt = f"{baja:.1f}% baja" if pd.notna(baja) else "—"
                        n_of = row.get("n_ofertas_recibidas")
                        n_of_txt = f"{int(n_of)} ofertas" if pd.notna(n_of) else "—"
                        fecha_adj = (row["fecha_adjudicacion"].date()
                                       if pd.notna(row["fecha_adjudicacion"])
                                       else "—")
                        st.markdown(
                            f'<div class="top-card">'
                            f'<div class="amount">'
                            f'{fmt_eur(row["importe_adjudicado"])}</div>'
                            f'<div class="title"><a href="{url}" target="_blank" '
                            f'style="color:#E0E0E0;text-decoration:none">'
                            f'{(row["titulo"] or "")[:120]}</a></div>'
                            f'<div class="meta">'
                            f'{row.get("organo_contratacion","—")} · '
                            f'Adj: {fecha_adj} · {baja_txt} · {n_of_txt}'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

# ─── Pipeline & Alertas ────────────────────────────────────────────────────
if page == "Pipeline & Alertas":
    st.subheader("Pipeline & Alertas")
    st.caption(
        "Previsión de re-licitaciones, contratos próximos a vencer y "
        "ventanas de oportunidad comercial.")

    adj_rv = load_adjudicaciones()
    if adj_rv.empty or df.empty:
        st.info("Sin datos de adjudicación disponibles.")
    else:
        from dashboard.forecast import (build_forecast_df,
                                         to_months, estimate_end_date)

        # ── Configuración ────────────────────────────────────────────────
        cRV1, cRV2, cRV3, cRV4 = st.columns(4)
        with cRV1:
            rv_horizonte = st.slider("Horizonte (meses)", 1, 36, 18,
                                      key="rv_horizonte")
        with cRV2:
            rv_ant = st.slider("Anticipación alerta (meses)", 1, 12, 6,
                                key="rv_ant")
        with cRV3:
            rv_imp_min = st.number_input("Importe mínimo (€)", min_value=0,
                                          value=0, step=50000,
                                          key="rv_imp_min")
        with cRV4:
            rv_solo_mant = st.checkbox("Solo Mantenimiento", value=False,
                                        key="rv_solo_mant",
                                        help="Desmarcar para ver todos los tipos")

        fc_rv = build_forecast_df(df, adj_rv,
                                   meses_anticipacion=rv_ant,
                                   solo_mantenimiento=rv_solo_mant)

        if fc_rv.empty or fc_rv["fecha_fin_estimada"].isna().all():
            st.info("Sin suficientes datos de duración / fecha_fin para construir el radar.")
        else:
            hoy_rv = pd.Timestamp.utcnow().tz_localize(None)
            horiz_fin = hoy_rv + pd.DateOffset(months=rv_horizonte)

            oport = fc_rv[
                (fc_rv["fecha_fin_estimada"] >= hoy_rv) &
                (fc_rv["fecha_fin_estimada"] <= horiz_fin)
            ].copy()

            if rv_imp_min > 0:
                oport = oport[oport["importe"].fillna(0) >= rv_imp_min]

            if "adjudicatarios" in oport.columns:
                oport = oport.rename(
                    columns={"adjudicatarios": "adjudicatario_actual"})

            # ── KPIs ─────────────────────────────────────────────────────
            en_ventana = oport[oport["relicit_inicio"] <= hoy_rv]
            kv1, kv2, kv3, kv4 = st.columns(4)
            kv1.markdown(kpi_card("Oportunidades detectadas",
                                   f"{len(oport):,}",
                                   delta=f"próx. {rv_horizonte} meses",
                                   icon="🎯"), unsafe_allow_html=True)
            kv2.markdown(kpi_card("Importe en juego",
                                   fmt_eur(oport["importe"].sum(skipna=True)),
                                   icon="💰"), unsafe_allow_html=True)
            kv3.markdown(kpi_card("Ya en ventana de alerta",
                                   f"{len(en_ventana):,}",
                                   delta="actuar ahora",
                                   delta_up=False, icon="🔴"),
                          unsafe_allow_html=True)
            kv4.markdown(kpi_card("Importe en ventana",
                                   fmt_eur(en_ventana["importe"].sum(
                                       skipna=True)),
                                   icon="🚨"), unsafe_allow_html=True)

            st.markdown("")

            # ── Distribución horizonte + Volumen trimestral ──────────────
            cFc1, cFc2 = st.columns(2)
            with cFc1:
                st.subheader("Distribución por horizonte temporal")
                ef = (fc_rv.dropna(subset=["estado_forecast"])
                         .groupby("estado_forecast", observed=True)
                         .agg(n=("id_externo", "count"),
                              importe=("importe", "sum"))
                         .reset_index())
                if not ef.empty:
                    fig = px.bar(ef, x="estado_forecast", y="n",
                                  template=PLOTLY_TEMPLATE,
                                  color="importe",
                                  color_continuous_scale="Greens",
                                  labels={"estado_forecast": "",
                                          "n": "Contratos",
                                          "importe": "Importe €"})
                    fig.update_layout(height=380,
                                       margin=dict(t=20, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)

            with cFc2:
                st.subheader("Volumen previsto por trimestre")
                qf = oport.dropna(subset=["fecha_fin_estimada"]).copy()
                if not qf.empty:
                    qf["trimestre"] = (qf["fecha_fin_estimada"]
                                         .dt.to_period("Q").dt.to_timestamp())
                    qg = (qf.groupby("trimestre")
                              .agg(n=("id_externo", "count"),
                                   importe=("importe", "sum"))
                              .reset_index())
                    fig = px.bar(qg, x="trimestre", y="importe",
                                  template=PLOTLY_TEMPLATE,
                                  color_discrete_sequence=["#86BC25"],
                                  labels={"trimestre": "",
                                          "importe": "Importe que vence (€)"},
                                  hover_data=["n"])
                    fig.update_layout(height=380,
                                       margin=dict(t=20, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)

            # ── Matriz urgencia × valor ──────────────────────────────────
            st.subheader("Matriz urgencia × valor del contrato")
            if not oport.empty:
                oport["dias_restantes"] = (
                    oport["fecha_fin_estimada"] - hoy_rv).dt.days
                oport_s = oport.dropna(subset=["importe", "dias_restantes"])
                if not oport_s.empty:
                    oport_s = oport_s.copy()
                    oport_s["label"] = oport_s["titulo"].str[:50]
                    oport_s["prorroga"] = (
                        oport_s["prorroga_descripcion"].notna()
                        if "prorroga_descripcion" in oport_s.columns
                        else False)
                    fig = px.scatter(
                        oport_s, x="dias_restantes", y="importe",
                        color="estado_forecast",
                        size="importe",
                        hover_name="label",
                        hover_data={"organo_contratacion": True,
                                    "dias_restantes": True,
                                    "importe": ":,.0f"},
                        template=PLOTLY_TEMPLATE,
                        color_discrete_sequence=COLOR_SEQUENCE,
                        log_y=True,
                        labels={"dias_restantes": "Días hasta vencimiento",
                                "importe": "Importe licitación (€, log)",
                                "estado_forecast": "Estado"})
                    # Línea vertical: inicio de ventana alerta
                    fig.add_vline(
                        x=rv_ant * 30, line_dash="dash",
                        line_color="#E21836",
                        annotation_text=f"Ventana alerta ({rv_ant}m)",
                        annotation_position="top right")
                    fig.update_layout(height=480,
                                      margin=dict(t=20, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Cuadrante **izquierda-arriba**: contratos grandes "
                               "con vencimiento inminente — máxima prioridad.")

            # ── Timeline Gantt ───────────────────────────────────────────
            st.subheader("Timeline de contratos (top 30 por valor)")
            tl_rv = oport.dropna(
                subset=["inicio_efectivo", "fecha_fin_estimada"]).copy()
            if not tl_rv.empty:
                tl_rv = tl_rv.nlargest(30, "importe")
                tl_rv["label"] = tl_rv["titulo"].str[:55]
                adj_col = ("adjudicatario_actual"
                            if "adjudicatario_actual" in tl_rv.columns
                            else None)
                hover_extra = ({"adjudicatario_actual": True}
                                if adj_col else {})
                fig = px.timeline(
                    tl_rv,
                    x_start="inicio_efectivo",
                    x_end="fecha_fin_estimada",
                    y="label", color="importe",
                    color_continuous_scale="YlGn",
                    template=PLOTLY_TEMPLATE,
                    hover_data={"organo_contratacion": True,
                                "importe": ":,.0f",
                                **hover_extra})
                fig.add_shape(
                    type="line",
                    x0=hoy_rv.isoformat(), x1=hoy_rv.isoformat(),
                    y0=0, y1=1, yref="paper",
                    line=dict(color="#E21836", dash="dash", width=2))
                fig.add_annotation(
                    x=hoy_rv.isoformat(), y=1, yref="paper",
                    text="Hoy", showarrow=False,
                    font=dict(color="#E21836"), yanchor="bottom")
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=620,
                                  margin=dict(t=20, b=10, l=10, r=10),
                                  yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

            # ── Tabla de oportunidades ───────────────────────────────────
            st.subheader("Listado de oportunidades")
            cols_rv = ["fecha_fin_estimada", "relicit_inicio", "titulo",
                        "organo_contratacion", "ccaa", "importe",
                        "estado_forecast"]
            if "adjudicatario_actual" in oport.columns:
                cols_rv.append("adjudicatario_actual")
            if "prorroga_descripcion" in oport.columns:
                cols_rv.append("prorroga_descripcion")
            if "url" in oport.columns:
                cols_rv.append("url")
            cols_rv = [c for c in cols_rv if c in oport.columns]
            st.dataframe(
                oport[cols_rv].sort_values("fecha_fin_estimada"),
                use_container_width=True, hide_index=True, height=480,
                column_config={
                    "fecha_fin_estimada": st.column_config.DateColumn(
                        "Fin estimado"),
                    "relicit_inicio": st.column_config.DateColumn(
                        "Inicio ventana"),
                    "titulo": st.column_config.TextColumn(
                        "Título", width="large"),
                    "organo_contratacion": st.column_config.TextColumn(
                        "Órgano", width="medium"),
                    "ccaa": st.column_config.TextColumn("CCAA",
                                                          width="small"),
                    "importe": st.column_config.NumberColumn(
                        "Importe lic.", format="%.0f €"),
                    "estado_forecast": st.column_config.TextColumn("Estado"),
                    "adjudicatario_actual": st.column_config.TextColumn(
                        "Adjudicatario actual", width="medium"),
                    "prorroga_descripcion": st.column_config.TextColumn(
                        "Prórroga"),
                    "url": st.column_config.LinkColumn(
                        "Enlace", display_text="🔗"),
                },
            )

# ── Footer ─────────────────────────────────────────────────────────────
st.divider()
ext = load_extracciones()
if not ext.empty:
    st.caption(f"📦 Última extracción: "
               f"{ext.iloc[0]['fecha']} — fuente "
               f"{ext.iloc[0]['fuente']} ({ext.iloc[0]['nuevas']} nuevas)")
st.caption("Fuente oficial: contrataciondelestado.es · "
           "Reutilización Ley 37/2007 · No suplanta a la fuente oficial.")
