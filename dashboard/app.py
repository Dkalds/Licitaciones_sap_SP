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
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
  h1, h2, h3 { font-weight: 600; }
  .kpi-card {
    background: linear-gradient(135deg, #1A1F2C 0%, #1F2937 100%);
    border: 1px solid rgba(0,180,216,0.15);
    border-radius: 12px; padding: 18px 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
  }
  .kpi-card .label { color: #9CA3AF; font-size: 0.78rem;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .kpi-card .value { color: #E8ECF1; font-size: 1.85rem;
    font-weight: 700; line-height: 1.1; }
  .kpi-card .delta { font-size: 0.85rem; margin-top: 4px; }
  .kpi-card .delta.up { color: #10B981; }
  .kpi-card .delta.down { color: #EF4444; }
  .kpi-card .icon { font-size: 1.2rem; opacity: 0.6; float: right; }
  .top-card {
    background: #1A1F2C; border-left: 4px solid #00B4D8;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
  }
  .top-card .amount { font-size: 1.4rem; font-weight: 700; color: #00B4D8; }
  .top-card .title { font-size: 0.95rem; color: #E8ECF1; margin: 4px 0; }
  .top-card .meta { font-size: 0.78rem; color: #9CA3AF; }
  div[data-testid="stMetricValue"] { font-size: 1.6rem; }
  .stTabs [data-baseweb="tab-list"] { gap: 4px; }
  .stTabs [data-baseweb="tab"] {
    background-color: #1A1F2C; border-radius: 8px 8px 0 0;
    padding: 8px 18px;
  }
  .stTabs [aria-selected="true"] { background-color: #00B4D8 !important; color: white !important; }
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

PLOTLY_TEMPLATE = "plotly_dark"
COLOR_SEQUENCE = px.colors.qualitative.Vivid

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
col_t, col_r = st.columns([6, 2])
with col_t:
    st.markdown("# 📊 Licitaciones SAP · Sector Público España")
    st.caption("Plataforma de Contratación del Sector Público — "
               "reutilización al amparo de la Ley 37/2007")
with col_r:
    if st.button("🔄 Refrescar caché", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

df_full = load_dataframe()

if df_full.empty:
    st.warning("No hay datos en la BD. Ejecuta:")
    st.code("python -m scheduler.run_update --backfill 2024 1")
    st.stop()

# ── Sidebar: filtros ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ Filtros")

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

# ── Tabs ─────────────────────────────────────────────────────────────────
(tab_resumen, tab_tendencias, tab_org, tab_geo,
 tab_proyectos, tab_adjudicatarios, tab_prevision,
 tab_detalle) = st.tabs(
    ["📌 Resumen", "📈 Tendencias", "🏛️ Órganos", "🗺️ Geografía",
     "🧩 Proyectos & módulos", "💼 Adjudicatarios",
     "📅 Previsión", "📋 Detalle"])

# ─── Tab Resumen ────────────────────────────────────────────────────────
with tab_resumen:
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
                f'style="color:#E8ECF1;text-decoration:none">'
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
                          color="n", color_continuous_scale="Teal",
                          labels={"n": "", "tipo_proyecto": ""})
            fig.update_layout(height=300, showlegend=False,
                               coloraxis_showscale=False,
                               margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

# ─── Tab Tendencias ─────────────────────────────────────────────────────
with tab_tendencias:
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
                          color_discrete_sequence=["#00B4D8"])
            fig.update_layout(height=380,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.area(g, x="mes", y="importe", template=PLOTLY_TEMPLATE,
                           labels={"mes": "Mes", "importe": "Importe (€)"},
                           color_discrete_sequence=["#10B981"])
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
                         color_continuous_scale="Teal",
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
            color_discrete_sequence=["#00B4D8"],
            labels={"importe_log": "Importe (€, log)"})
        fig.update_layout(height=320,
                           margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

# ─── Tab Órganos ────────────────────────────────────────────────────────
with tab_org:
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
                          color_continuous_scale="Tealgrn",
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
                          color="n", color_continuous_scale="Pubu",
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
            color="importe", color_continuous_scale="Teal")
        fig.update_layout(height=600,
                           margin=dict(t=20, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

# ─── Tab Geografía ──────────────────────────────────────────────────────
with tab_geo:
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
                          color="importe", color_continuous_scale="Teal",
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
with tab_proyectos:
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
                          color_continuous_scale="Aggrnyl",
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
                                color="n", color_continuous_scale="Teal")
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

# ─── Tab Adjudicatarios ─────────────────────────────────────────────────
with tab_adjudicatarios:
    adj_full = load_adjudicaciones()

    # Restringir adjudicaciones a las licitaciones filtradas en sidebar
    if not adj_full.empty:
        ids_filtrados = set(df["id_externo"])
        adj = adj_full[adj_full["licitacion_id"].isin(ids_filtrados)].copy()
    else:
        adj = adj_full

    if adj.empty:
        st.info("Aún no hay datos de adjudicación. Las licitaciones en estado "
                 "ADJ/RES son las que traen información del adjudicatario.")
    else:
        # ── KPIs ──
        n_adj = len(adj)
        n_empresas = adj["empresa_key"].dropna().nunique()
        importe_adj_total = adj["importe_adjudicado"].sum(skipna=True)
        pct_pyme = ((adj["es_pyme"] == 1).sum() /
                     adj["es_pyme"].notna().sum() * 100
                     if adj["es_pyme"].notna().any() else 0)

        # Top empresa por importe (agrupado por empresa_key)
        top_emp = (adj.groupby("nombre_canonico")["importe_adjudicado"].sum()
                       .sort_values(ascending=False))
        top_nombre = top_emp.index[0] if len(top_emp) else "—"
        top_importe = top_emp.iloc[0] if len(top_emp) else 0

        # Ahorro medio (importe licitación vs adjudicado)
        with_lic = adj.merge(
            df[["id_externo", "importe"]].rename(
                columns={"importe": "importe_lic"}),
            left_on="licitacion_id", right_on="id_externo", how="left")
        ahorro_pct = None
        valid = with_lic.dropna(subset=["importe_lic", "importe_adjudicado"])
        valid = valid[valid["importe_lic"] > 0]
        if not valid.empty:
            ahorros = (1 - valid["importe_adjudicado"] / valid["importe_lic"])
            ahorro_pct = ahorros.median() * 100

        kc1, kc2, kc3, kc4, kc5 = st.columns(5)
        kc1.markdown(kpi_card("Adjudicaciones", f"{n_adj:,}", icon="✍️"),
                       unsafe_allow_html=True)
        kc2.markdown(kpi_card("Empresas únicas", f"{n_empresas:,}",
                               icon="🏢"), unsafe_allow_html=True)
        kc3.markdown(kpi_card("Importe adjudicado",
                               fmt_eur(importe_adj_total), icon="💸"),
                       unsafe_allow_html=True)
        kc4.markdown(kpi_card("% adjudicado a PYMEs",
                               f"{pct_pyme:.0f}%", icon="🏭"),
                       unsafe_allow_html=True)
        if ahorro_pct is not None:
            delta_up = ahorro_pct > 0
            kc5.markdown(kpi_card("Baja media (lic→adj)",
                                    f"{ahorro_pct:.1f}%",
                                    delta="vs precio licitación",
                                    delta_up=delta_up, icon="📉"),
                          unsafe_allow_html=True)
        else:
            kc5.markdown(kpi_card("Baja media", "—", icon="📉"),
                          unsafe_allow_html=True)

        st.markdown("")

        # ── Top empresas ──
        cT1, cT2 = st.columns(2)
        with cT1:
            st.subheader("Top 15 empresas por importe adjudicado")
            top_imp = (adj.groupby("nombre_canonico")
                          .agg(importe=("importe_adjudicado", "sum"),
                               n=("id", "count"))
                          .reset_index()
                          .rename(columns={"nombre_canonico": "nombre"})
                          .sort_values("importe", ascending=False)
                          .head(15))
            if not top_imp.empty:
                fig = px.bar(top_imp.sort_values("importe"),
                              x="importe", y="nombre", orientation="h",
                              template=PLOTLY_TEMPLATE,
                              color="n", color_continuous_scale="Aggrnyl",
                              labels={"importe": "Importe €",
                                      "nombre": "",
                                      "n": "Nº contratos"},
                              hover_data=["n"])
                fig.update_layout(height=520,
                                   margin=dict(t=20, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
        with cT2:
            st.subheader("Top 15 empresas por nº contratos")
            top_n = (adj.groupby("nombre_canonico")
                        .agg(n=("id", "count"),
                             importe=("importe_adjudicado", "sum"))
                        .reset_index()
                        .rename(columns={"nombre_canonico": "nombre"})
                        .sort_values("n", ascending=False)
                        .head(15))
            if not top_n.empty:
                fig = px.bar(top_n.sort_values("n"),
                              x="n", y="nombre", orientation="h",
                              template=PLOTLY_TEMPLATE,
                              color="importe",
                              color_continuous_scale="Pubu",
                              labels={"n": "Nº contratos", "nombre": "",
                                      "importe": "Importe €"},
                              hover_data=["importe"])
                fig.update_layout(height=520,
                                   margin=dict(t=20, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

        # ── PYMEs + concentración + competencia ──
        cP1, cP2, cP3 = st.columns(3)
        with cP1:
            st.subheader("PYME vs no-PYME")
            sme = adj.dropna(subset=["es_pyme"]).copy()
            sme["categoria"] = sme["es_pyme"].map({1: "PYME",
                                                      0: "No PYME"})
            if not sme.empty:
                gr = (sme.groupby("categoria")
                          .agg(n=("id", "count"),
                               importe=("importe_adjudicado", "sum"))
                          .reset_index())
                fig = px.pie(gr, names="categoria", values="importe",
                              hole=0.55, template=PLOTLY_TEMPLATE,
                              color_discrete_sequence=["#10B981", "#F59E0B"])
                fig.update_traces(textinfo="label+percent")
                fig.update_layout(height=320,
                                   margin=dict(t=10, b=10, l=10, r=10),
                                   showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Sin indicador PYME en los datos")

        with cP2:
            st.subheader("Concentración (Pareto)")
            top_cum = (adj.groupby("nombre_canonico")["importe_adjudicado"]
                          .sum().sort_values(ascending=False))
            if len(top_cum) > 0:
                cum_pct = (top_cum.cumsum() / top_cum.sum() * 100).values
                rank_pct = ((1 + pd.Series(range(len(top_cum)))) /
                              len(top_cum) * 100).values
                pareto = pd.DataFrame({"empresas_pct": rank_pct,
                                        "importe_pct": cum_pct})
                fig = px.area(pareto, x="empresas_pct", y="importe_pct",
                               template=PLOTLY_TEMPLATE,
                               color_discrete_sequence=["#00B4D8"],
                               labels={"empresas_pct": "% empresas",
                                       "importe_pct": "% importe acumulado"})
                fig.update_layout(height=320,
                                   margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
                # Métricas concretas
                top10 = (top_cum.head(10).sum() /
                          top_cum.sum() * 100) if top_cum.sum() else 0
                st.caption(f"📊 **Top 10 empresas captan el "
                            f"{top10:.0f}%** del importe adjudicado")

        with cP3:
            st.subheader("Nº ofertas recibidas")
            ofertas = adj.dropna(subset=["n_ofertas_recibidas"])
            if not ofertas.empty:
                fig = px.histogram(
                    ofertas, x="n_ofertas_recibidas",
                    nbins=20, template=PLOTLY_TEMPLATE,
                    color_discrete_sequence=["#00B4D8"],
                    labels={"n_ofertas_recibidas": "Ofertas por concurso"})
                fig.update_layout(height=320,
                                   margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📊 Mediana: "
                            f"**{ofertas['n_ofertas_recibidas'].median():.0f} "
                            f"ofertas** por adjudicación")

        # ── CCAA origen empresas ──
        st.subheader("Origen de los adjudicatarios por CCAA")
        ccaa_adj = (adj.dropna(subset=["ccaa"])
                       .groupby("ccaa")
                       .agg(n=("id", "count"),
                            importe=("importe_adjudicado", "sum"),
                            empresas=("empresa_key", "nunique"))
                       .reset_index()
                       .sort_values("importe", ascending=False))
        if not ccaa_adj.empty:
            fig = px.bar(ccaa_adj.sort_values("importe"),
                          x="importe", y="ccaa", orientation="h",
                          template=PLOTLY_TEMPLATE,
                          color="empresas",
                          color_continuous_scale="Teal",
                          labels={"importe": "Importe adjudicado €",
                                  "ccaa": "",
                                  "empresas": "Empresas únicas"},
                          hover_data=["n"])
            fig.update_layout(height=420,
                               margin=dict(t=20, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

        # ── Métricas comparativas por empresa ──
        st.divider()
        st.subheader("📊 Métricas comparativas por empresa")
        st.caption("Para estudiar rentabilidad y perfil competitivo. "
                    "Solo empresas con al menos 2 adjudicaciones.")

        def _pct_top_organo(s: pd.Series) -> float:
            if s.empty:
                return 0.0
            counts = s.value_counts(normalize=True)
            return float(counts.iloc[0] * 100)

        adj_m = adj.copy()
        adj_m["es_monopolio"] = (adj_m["n_ofertas_recibidas"] == 1).astype(int)
        adj_m["año"] = adj_m["fecha_adjudicacion"].dt.year

        metr = (adj_m.groupby("empresa_key", dropna=False)
                       .agg(empresa=("nombre_canonico", "first"),
                            nif=("nif_norm", "first"),
                            contratos=("id", "count"),
                            importe_total=("importe_adjudicado", "sum"),
                            importe_medio=("importe_adjudicado", "mean"),
                            importe_mediano=("importe_adjudicado", "median"),
                            baja_media=("baja_pct", "mean"),
                            baja_mediana=("baja_pct", "median"),
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
            metr["antiguedad_años"] = antig_años.round(1)
            metr["contratos_año"] = (metr["contratos"] / antig_años).round(1)
            total_imp = metr["importe_total"].sum()
            metr["cuota_pct"] = (
                metr["importe_total"] / total_imp * 100
                if total_imp else 0)
            metr = metr.sort_values("importe_total", ascending=False)

            cols_show = ["empresa", "nif", "contratos", "contratos_año",
                          "antiguedad_años", "importe_total", "cuota_pct",
                          "importe_medio", "importe_mediano",
                          "baja_media", "baja_mediana",
                          "ofertas_medias", "pct_monopolio",
                          "organos", "pct_top_organo", "ultima"]
            st.dataframe(
                metr[cols_show].head(100),
                use_container_width=True, hide_index=True, height=420,
                column_config={
                    "empresa": st.column_config.TextColumn("Empresa",
                                                             width="large"),
                    "nif": st.column_config.TextColumn("NIF",
                                                        width="small"),
                    "contratos": st.column_config.NumberColumn("Contratos"),
                    "contratos_año": st.column_config.NumberColumn(
                        "Contr./año",
                        help="Ritmo de adjudicaciones por año activo"),
                    "antiguedad_años": st.column_config.NumberColumn(
                        "Antigüedad",
                        help="Años entre primera y última adjudicación"),
                    "importe_total": st.column_config.NumberColumn(
                        "Importe total", format="%.0f €"),
                    "cuota_pct": st.column_config.NumberColumn(
                        "Cuota %", format="%.1f%%",
                        help="% sobre importe adjudicado total del filtro"),
                    "importe_medio": st.column_config.NumberColumn(
                        "Imp. medio", format="%.0f €"),
                    "importe_mediano": st.column_config.NumberColumn(
                        "Imp. mediano", format="%.0f €"),
                    "baja_media": st.column_config.NumberColumn(
                        "Baja media", format="%.1f%%",
                        help="Agresividad media en oferta"),
                    "baja_mediana": st.column_config.NumberColumn(
                        "Baja mediana", format="%.1f%%"),
                    "ofertas_medias": st.column_config.NumberColumn(
                        "Ofertas enfrent.", format="%.1f",
                        help="Competencia media a la que se enfrentó"),
                    "pct_monopolio": st.column_config.NumberColumn(
                        "% Monopolio", format="%.0f%%",
                        help="% de sus contratos con 1 sola oferta"),
                    "organos": st.column_config.NumberColumn("Órganos"),
                    "pct_top_organo": st.column_config.NumberColumn(
                        "% top-1 órgano", format="%.0f%%",
                        help="Dependencia del cliente principal"),
                    "ultima": st.column_config.DateColumn("Última adj."),
                },
            )

            # Scatter: posicionamiento competitivo
            st.markdown("##### 🎯 Mapa de posicionamiento competitivo")
            scatter = metr.dropna(
                subset=["importe_medio", "baja_media"]).head(60)
            if not scatter.empty:
                fig = px.scatter(
                    scatter, x="baja_media", y="importe_medio",
                    size="contratos", color="pct_monopolio",
                    hover_name="empresa",
                    hover_data={"contratos": True,
                                  "importe_total": ":,.0f",
                                  "ofertas_medias": ":.1f",
                                  "pct_monopolio": ":.0f"},
                    template=PLOTLY_TEMPLATE,
                    color_continuous_scale="RdYlGn_r", log_y=True,
                    labels={"baja_media": "Baja media (%) — agresividad",
                              "importe_medio": "Importe medio por contrato (€, log)",
                              "pct_monopolio": "% monopolio"})
                fig.update_layout(height=520,
                                   margin=dict(t=20, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
                st.caption("📍 Cuadrante **arriba-derecha**: contratos grandes "
                            "con baja agresiva (alta competencia). "
                            "**Arriba-izquierda con color rojo**: contratos "
                            "grandes sin competencia (clientes cautivos). "
                            "Tamaño de burbuja = volumen de contratos.")
        else:
            st.info("Necesitas empresas con ≥2 adjudicaciones para "
                     "calcular métricas comparativas.")

        # ── Tabla buscable + drill-down por empresa ──
        st.divider()
        st.subheader("🔍 Buscador de empresas")
        empresa_q = st.text_input(
            "Filtrar por nombre o NIF",
            placeholder="Ej: TELEFONICA, INDRA, B12345678...",
            key="empresa_search",
        )
        ranking = (adj.groupby("empresa_key", dropna=False)
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
            use_container_width=True, hide_index=True,
            column_config={
                "nombre": st.column_config.TextColumn("Empresa",
                                                       width="large"),
                "nif": st.column_config.TextColumn("NIF/CIF",
                                                    width="small"),
                "variantes": st.column_config.NumberColumn(
                    "Variantes nombre",
                    help="Nº de grafías distintas agrupadas"),
                "contratos": st.column_config.NumberColumn("Contratos"),
                "importe_total": st.column_config.NumberColumn(
                    "Importe €", format="%.0f €"),
                "organos": st.column_config.NumberColumn("Órganos"),
                "ultima": st.column_config.DateColumn("Última adj."),
            },
            height=350,
        )

        # ── Drill-down: seleccionar varias empresas para comparar ──
        st.divider()
        st.subheader("🔬 Drill-down por empresa(s)")
        opciones_df = ranking[["nombre", "empresa_key"]].head(200)
        opciones = opciones_df["nombre"].tolist()
        empresas_sel = st.multiselect(
            "Selecciona una o varias empresas",
            options=opciones,
            placeholder="Empieza a escribir o elige del listado…",
        )
        if empresas_sel:
            keys_sel = opciones_df[
                opciones_df["nombre"].isin(empresas_sel)]["empresa_key"].tolist()
            sub = adj[adj["empresa_key"].isin(keys_sel)].copy()

            # KPIs agregados
            cE1, cE2, cE3, cE4 = st.columns(4)
            cE1.metric("Empresas", len(empresas_sel))
            cE2.metric("Contratos", len(sub))
            cE3.metric("Importe total",
                        fmt_eur(sub["importe_adjudicado"].sum()))
            cE4.metric("Órganos distintos",
                        sub["organo_contratacion"].nunique())

            # Tabla comparativa
            comp = (sub.groupby("empresa_key")
                       .agg(nombre=("nombre_canonico", "first"),
                            contratos=("id", "count"),
                            importe=("importe_adjudicado", "sum"),
                            organos=("organo_contratacion", "nunique"),
                            primera=("fecha_adjudicacion", "min"),
                            ultima=("fecha_adjudicacion", "max"))
                       .reset_index(drop=True)
                       .sort_values("importe", ascending=False))
            st.dataframe(
                comp, use_container_width=True, hide_index=True,
                column_config={
                    "nombre": st.column_config.TextColumn("Empresa",
                                                            width="large"),
                    "contratos": st.column_config.NumberColumn("Contratos"),
                    "importe": st.column_config.NumberColumn(
                        "Importe €", format="%.0f €"),
                    "organos": st.column_config.NumberColumn("Órganos"),
                    "primera": st.column_config.DateColumn("Primera adj."),
                    "ultima": st.column_config.DateColumn("Última adj."),
                },
            )

            # Métricas comparativas de las empresas seleccionadas
            if "empresa_key" in metr.columns or not metr.empty:
                comp_metr = metr[metr["empresa"].isin(
                    [opciones_df[opciones_df["nombre"] == e]["nombre"].iloc[0]
                     for e in empresas_sel])]
                if not comp_metr.empty:
                    st.markdown("##### 📐 Métricas comparativas")
                    cols_min = ["empresa", "contratos", "importe_medio",
                                 "baja_media", "ofertas_medias",
                                 "pct_monopolio", "pct_top_organo",
                                 "contratos_año"]
                    st.dataframe(
                        comp_metr[cols_min], use_container_width=True,
                        hide_index=True,
                        column_config={
                            "empresa": st.column_config.TextColumn("Empresa"),
                            "contratos": st.column_config.NumberColumn(
                                "Contratos"),
                            "importe_medio": st.column_config.NumberColumn(
                                "Imp. medio", format="%.0f €"),
                            "baja_media": st.column_config.NumberColumn(
                                "Baja media", format="%.1f%%"),
                            "ofertas_medias": st.column_config.NumberColumn(
                                "Ofertas enfrent.", format="%.1f"),
                            "pct_monopolio": st.column_config.NumberColumn(
                                "% Monopolio", format="%.0f%%"),
                            "pct_top_organo": st.column_config.NumberColumn(
                                "% top-1 órgano", format="%.0f%%"),
                            "contratos_año": st.column_config.NumberColumn(
                                "Contr./año"),
                        },
                    )

            # Comparativa visual cuando hay >1 empresa
            if len(empresas_sel) > 1:
                cV1, cV2 = st.columns(2)
                with cV1:
                    fig = px.bar(comp.sort_values("importe"),
                                  x="importe", y="nombre", orientation="h",
                                  template=PLOTLY_TEMPLATE,
                                  color="contratos",
                                  color_continuous_scale="Aggrnyl",
                                  labels={"importe": "Importe €",
                                          "nombre": "",
                                          "contratos": "Contratos"})
                    fig.update_layout(
                        height=350,
                        margin=dict(t=20, b=10, l=10, r=10),
                        title="Importe acumulado")
                    st.plotly_chart(fig, use_container_width=True)
                with cV2:
                    # Evolución temporal por empresa
                    if sub["fecha_adjudicacion"].notna().any():
                        evo = (sub.dropna(subset=["fecha_adjudicacion"])
                                  .assign(mes=lambda x: x["fecha_adjudicacion"]
                                          .dt.to_period("M").dt.to_timestamp())
                                  .groupby(["mes", "nombre_canonico"])
                                  ["importe_adjudicado"].sum()
                                  .reset_index()
                                  .rename(columns={
                                      "nombre_canonico": "nombre"}))
                        fig = px.line(
                            evo, x="mes", y="importe_adjudicado",
                            color="nombre", markers=True,
                            template=PLOTLY_TEMPLATE,
                            color_discrete_sequence=COLOR_SEQUENCE,
                            labels={"mes": "Mes",
                                    "importe_adjudicado": "Importe €"})
                        fig.update_layout(
                            height=350,
                            margin=dict(t=20, b=10, l=10, r=10),
                            title="Evolución temporal",
                            legend=dict(orientation="h", y=-0.2))
                        st.plotly_chart(fig, use_container_width=True)

            # Listado de proyectos (agrupado por empresa si son varias)
            st.markdown("##### 📋 Proyectos adjudicados")
            st.caption("ℹ️ La plataforma solo publica el adjudicatario, "
                        "no el listado de licitadores que se presentaron.")
            for empresa in empresas_sel:
                key = opciones_df[
                    opciones_df["nombre"] == empresa]["empresa_key"].iloc[0]
                empresa_proyectos = sub[sub["empresa_key"] == key]
                if len(empresas_sel) > 1:
                    st.markdown(f"**🏢 {empresa}** "
                                  f"({len(empresa_proyectos)} contratos · "
                                  f"{fmt_eur(empresa_proyectos['importe_adjudicado'].sum())})")
                for _, row in empresa_proyectos.sort_values(
                        "importe_adjudicado", ascending=False).iterrows():
                    url = row.get("url_lic") or "#"
                    baja = row.get("baja_pct")
                    baja_txt = (f"📉 {baja:.1f}% baja"
                                  if pd.notna(baja) else "—")
                    imp_lic = row.get("importe_licitacion")
                    imp_lic_txt = (f"Lic: {fmt_eur(imp_lic)} · "
                                     if pd.notna(imp_lic) else "")
                    n_of = row.get("n_ofertas_recibidas")
                    n_of_txt = (f"{int(n_of)} ofertas"
                                  if pd.notna(n_of) else "ofertas: —")
                    fecha_adj = (row["fecha_adjudicacion"].date()
                                   if pd.notna(row["fecha_adjudicacion"])
                                   else "—")
                    pyme_txt = "· PYME" if row.get("es_pyme") == 1 else ""
                    st.markdown(
                        f'<div class="top-card">'
                        f'<div class="amount">'
                        f'{fmt_eur(row["importe_adjudicado"])}</div>'
                        f'<div class="title"><a href="{url}" target="_blank" '
                        f'style="color:#E8ECF1;text-decoration:none">'
                        f'{(row["titulo"] or "")[:120]}</a></div>'
                        f'<div class="meta">'
                        f'{row.get("organo_contratacion","—")} · '
                        f'Adj: {fecha_adj} · '
                        f'{imp_lic_txt}{baja_txt} · '
                        f'{n_of_txt} {pyme_txt}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

# ─── Tab Previsión ──────────────────────────────────────────────────────
with tab_prevision:
    st.subheader("📅 Previsión de re-licitaciones de mantenimiento")
    st.caption("Estimación de cuándo saldrán nuevos contratos de "
               "mantenimiento a partir de la finalización de los actuales. "
               "Solo se consideran proyectos clasificados como "
               "*Mantenimiento*.")

    cP1, cP2 = st.columns([1, 3])
    with cP1:
        meses_ant = st.slider("Meses de anticipación", 1, 18, 6,
                                help="Antelación con la que se prevé "
                                "que el órgano vuelva a licitar.")
    with cP2:
        horizonte_meses = st.slider("Horizonte (meses)", 3, 36, 18,
                                      help="Solo muestra contratos que "
                                      "terminen dentro de este horizonte.")

    adj_full = load_adjudicaciones()
    fc = build_forecast_df(df, adj_full, meses_anticipacion=meses_ant)

    if fc.empty or fc["fecha_fin_estimada"].isna().all():
        st.info("No hay suficientes datos de duración / fecha_fin para "
                 "construir la previsión. Ejecuta el backfill con el parser "
                 "actualizado para poblar esos campos.")
    else:
        # Cobertura
        total_mant = (df["tipo_proyecto"] == "Mantenimiento").sum()
        con_fecha = fc["fecha_fin_estimada"].notna().sum()
        cobertura = (con_fecha / total_mant * 100) if total_mant else 0

        hoy = pd.Timestamp.utcnow().tz_localize(None)
        horizonte_fin = hoy + pd.DateOffset(months=horizonte_meses)
        en_horizonte = fc[(fc["fecha_fin_estimada"] >= hoy) &
                            (fc["fecha_fin_estimada"] <= horizonte_fin)].copy()
        en_ventana = fc[(fc["relicit_inicio"] <= hoy) &
                          (fc["fecha_fin_estimada"] >= hoy)].copy()

        importe_riesgo = en_horizonte["importe"].sum(skipna=True)
        importe_ventana = en_ventana["importe"].sum(skipna=True)

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.markdown(kpi_card("Mantenim. analizados",
                               f"{con_fecha:,}/{total_mant:,}",
                               delta=f"{cobertura:.0f}% cobertura",
                               delta_up=cobertura >= 60, icon="📊"),
                      unsafe_allow_html=True)
        k2.markdown(kpi_card("Vencen en horizonte",
                               f"{len(en_horizonte):,}",
                               delta=f"próx. {horizonte_meses} meses",
                               icon="⏳"), unsafe_allow_html=True)
        k3.markdown(kpi_card("Importe en horizonte",
                               fmt_eur(importe_riesgo), icon="💰"),
                      unsafe_allow_html=True)
        k4.markdown(kpi_card("Ya en ventana relicit.",
                               f"{len(en_ventana):,}",
                               delta="oportunidad inmediata",
                               icon="🎯"), unsafe_allow_html=True)
        k5.markdown(kpi_card("Importe en ventana",
                               fmt_eur(importe_ventana), icon="🚨"),
                      unsafe_allow_html=True)

        st.markdown("")

        # Distribución por estado_forecast
        cD1, cD2 = st.columns(2)
        with cD1:
            st.subheader("Distribución por horizonte temporal")
            ef = (fc.dropna(subset=["estado_forecast"])
                     .groupby("estado_forecast", observed=True)
                     .agg(n=("id_externo", "count"),
                          importe=("importe", "sum"))
                     .reset_index())
            if not ef.empty:
                fig = px.bar(ef, x="estado_forecast", y="n",
                              template=PLOTLY_TEMPLATE,
                              color="importe",
                              color_continuous_scale="Sunsetdark",
                              labels={"estado_forecast": "",
                                      "n": "Contratos",
                                      "importe": "Importe €"})
                fig.update_layout(height=380,
                                   margin=dict(t=20, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

        with cD2:
            st.subheader("Volumen previsto por trimestre")
            qf = en_horizonte.dropna(subset=["fecha_fin_estimada"]).copy()
            if not qf.empty:
                qf["trimestre"] = (qf["fecha_fin_estimada"]
                                     .dt.to_period("Q").dt.to_timestamp())
                qg = (qf.groupby("trimestre")
                          .agg(n=("id_externo", "count"),
                               importe=("importe", "sum"))
                          .reset_index())
                fig = px.bar(qg, x="trimestre", y="importe",
                              template=PLOTLY_TEMPLATE,
                              color_discrete_sequence=["#00B4D8"],
                              labels={"trimestre": "",
                                      "importe": "Importe que vence (€)"},
                              hover_data=["n"])
                fig.update_layout(height=380,
                                   margin=dict(t=20, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

        # Gantt / timeline
        st.subheader("Timeline de contratos próximos a vencer")
        tl = en_horizonte.dropna(
            subset=["inicio_efectivo", "fecha_fin_estimada"]).copy()
        if not tl.empty:
            tl = tl.nlargest(30, "importe")
            tl["label"] = tl["titulo"].str[:60]
            fig = px.timeline(
                tl, x_start="inicio_efectivo", x_end="fecha_fin_estimada",
                y="label", color="importe",
                color_continuous_scale="Teal",
                template=PLOTLY_TEMPLATE,
                hover_data={"organo_contratacion": True,
                             "importe": ":,.0f",
                             "relicit_inicio": True,
                             "label": False})
            fig.add_shape(
                type="line", x0=hoy.isoformat(), x1=hoy.isoformat(),
                y0=0, y1=1, yref="paper",
                line=dict(color="#EF4444", dash="dash"))
            fig.add_annotation(
                x=hoy.isoformat(), y=1, yref="paper",
                text="Hoy", showarrow=False,
                font=dict(color="#EF4444"), yanchor="bottom")
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=600,
                               margin=dict(t=20, b=10, l=10, r=10),
                               yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        # Listado de oportunidades
        st.subheader("🎯 Próximas oportunidades de re-licitación")
        st.caption("⚠️ La plataforma solo publica el adjudicatario, no el "
                    "listado de empresas que se presentaron. Sí publica el "
                    "número total de ofertas recibidas.")
        op = en_horizonte.sort_values("fecha_fin_estimada").copy()
        op = op.rename(columns={"adjudicatarios": "adjudicatario_actual"})
        if not op.empty:
            cols_op = ["fecha_fin_estimada", "relicit_inicio", "titulo",
                        "organo_contratacion", "ccaa", "importe",
                        "importe_adjudicado_total", "baja_pct", "n_ofertas",
                        "adjudicatario_actual", "estado_forecast", "url"]
            cols_op = [c for c in cols_op if c in op.columns]
            st.dataframe(
                op[cols_op], use_container_width=True, hide_index=True,
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
                    "importe_adjudicado_total": st.column_config.NumberColumn(
                        "Importe adj.", format="%.0f €"),
                    "baja_pct": st.column_config.NumberColumn(
                        "% Baja", format="%.1f%%",
                        help="Diferencia entre importe licitación y "
                              "adjudicación"),
                    "n_ofertas": st.column_config.NumberColumn(
                        "Nº ofertas",
                        help="Empresas que presentaron oferta"),
                    "adjudicatario_actual": st.column_config.TextColumn(
                        "Adjudicatario actual", width="medium"),
                    "estado_forecast": st.column_config.TextColumn(
                        "Estado"),
                    "url": st.column_config.LinkColumn(
                        "Enlace", display_text="🔗"),
                },
                height=500,
            )


# ─── Tab Detalle ────────────────────────────────────────────────────────
with tab_detalle:
    st.subheader(f"Detalle de licitaciones ({len(df)})")

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

# ── Footer ─────────────────────────────────────────────────────────────
st.divider()
ext = load_extracciones()
if not ext.empty:
    st.caption(f"📦 Última extracción: "
               f"{ext.iloc[0]['fecha']} — fuente "
               f"{ext.iloc[0]['fuente']} ({ext.iloc[0]['nuevas']} nuevas)")
st.caption("Fuente oficial: contrataciondelestado.es · "
           "Reutilización Ley 37/2007 · No suplanta a la fuente oficial.")
