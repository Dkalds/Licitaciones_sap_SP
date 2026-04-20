"""Generador del bloque `<style>` inyectado en Streamlit.

`build_css(tokens)` devuelve la cadena `<style>…</style>` completa incluyendo:
- Estilos base (Fase 1)
- Shimmer animation para loading skeletons (Fase 3)
- Media queries responsive 1024 / 640 px (Fase 3)
- prefers-reduced-motion (Fase 3)
- Focus-visible ring y skip-to-content (Fase 4)
"""

from __future__ import annotations

from dashboard.theme.tokens import TOKENS, Tokens


def build_css(t: Tokens = TOKENS) -> str:
    c = t.colors
    ty = t.type
    ra = t.radii
    la = t.layout
    bp = t.breakpoints
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  /* ── Density (Fase 6) ─────────────────────────────────────────────── */
  :root {{ --density: 1; }}

  /* ── Base ─────────────────────────────────────────────────────────── */
  html, body, [class*="css"] {{
    font-family: {ty.family_sans} !important;
  }}
  .block-container {{
    padding-top: {la.container_padding_top};
    padding-bottom: {la.container_padding_bottom};
    max-width: {la.container_max_width};
  }}
  h1, h2, h3, h4 {{
    font-weight: {ty.weight_semibold} !important;
    letter-spacing: {ty.letter_tight};
    font-family: 'Inter', sans-serif !important;
    color: {c.text_primary} !important;
  }}
  h1 {{ font-size: {ty.size_xl} !important; }}
  h2 {{ font-size: {ty.size_lg} !important; color: {c.text_secondary} !important; }}

  /* ── Ocultar navegación nativa multipage de Streamlit ────────────── */
  [data-testid="stSidebarNav"] {{ display: none !important; }}
  [data-testid="stSidebarNavSeparator"] {{ display: none !important; }}

  /* ── Sidebar ──────────────────────────────────────────────────────── */
  section[data-testid="stSidebar"] {{
    width: {la.sidebar_width} !important;
    min-width: {la.sidebar_width} !important;
    max-width: {la.sidebar_width} !important;
    background: linear-gradient(180deg, {c.bg_sidebar_top} 0%, {c.bg_sidebar_bottom} 100%) !important;
    border-right: 1px solid {c.border_subtle} !important;
  }}
  section[data-testid="stSidebar"] > div {{ padding-top: {t.spacing.lg}; }}

  /* ── KPI Cards ────────────────────────────────────────────────────── */
  .kpi-card {{
    background: {c.bg_elev_1};
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid {c.border_subtle};
    border-radius: {ra.md};
    padding: calc(18px * var(--density)) calc(22px * var(--density));
    box-shadow: {t.shadows.md};
    transition: border-color 0.2s, transform 0.15s;
  }}
  .kpi-card:hover {{ border-color: {c.accent_primary}; transform: translateY(-1px); }}
  .kpi-card .label {{
    color: {c.text_muted}; font-size: {ty.size_xs}; font-weight: {ty.weight_medium};
    text-transform: uppercase; letter-spacing: {ty.letter_kpi_label};
    margin-bottom: calc(6px * var(--density));
  }}
  .kpi-card .value {{
    color: {c.text_value}; font-size: {ty.size_2xl}; font-weight: {ty.weight_bold};
    line-height: 1.1; letter-spacing: -0.02em;
  }}
  .kpi-card .delta {{ font-size: 0.76rem; margin-top: calc(6px * var(--density)); font-weight: {ty.weight_medium}; }}
  .kpi-card .delta.up {{ color: {c.accent_primary}; }}
  .kpi-card .delta.down {{ color: {c.danger}; }}
  .kpi-card .icon {{ font-size: 1rem; opacity: 0.35; float: right; }}
  .kpi-card .anomaly-badge {{
    float: right; margin-right: 6px; font-size: 0.9rem;
    color: {c.danger}; cursor: help; line-height: 1;
  }}
  .kpi-card .sparkline-wrap {{
    margin-top: calc(6px * var(--density)); line-height: 0;
    opacity: 0.85;
  }}
  .kpi-card .sparkline {{ display: block; }}
  .kpi-card[title] {{ cursor: help; }}

  /* ── Top cards ────────────────────────────────────────────────────── */
  .top-card {{
    background: {c.bg_elev_2};
    border: 1px solid {c.border_card};
    border-left: 3px solid {c.accent_primary};
    border-radius: {ra.md};
    padding: calc(14px * var(--density)) calc(18px * var(--density));
    margin-bottom: calc(8px * var(--density));
    transition: border-color 0.15s;
  }}
  .top-card:hover {{ border-color: {c.border_hover}; border-left-color: {c.accent_primary_hover}; }}
  .top-card .amount {{ font-size: 1.25rem; font-weight: {ty.weight_bold}; color: {c.accent_primary}; letter-spacing: -0.01em; }}
  .top-card .title {{ font-size: 0.88rem; color: {c.text_card_title}; margin: 4px 0; line-height: 1.35; }}
  .top-card .meta {{ font-size: 0.74rem; color: {c.text_muted}; }}

  /* ── Breadcrumb ───────────────────────────────────────────────────── */
  .bc {{ font-size: {ty.size_sm}; margin-bottom: 2px; }}
  .bc-section {{ color: {c.text_muted}; font-weight: {ty.weight_medium}; }}
  .bc-sep {{ color: {c.text_disabled}; margin: 0 4px; }}
  .bc-page {{ color: {c.accent_primary}; font-weight: {ty.weight_medium}; }}

  /* ── Metrics & misc ───────────────────────────────────────────────── */
  div[data-testid="stMetricValue"] {{ font-size: 1.5rem; }}
  .stDivider {{ opacity: 0.3; }}
  ::-webkit-scrollbar {{ width: 5px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: {c.scrollbar_thumb}; border-radius: 3px; }}

  /* ── Loading skeleton shimmer ─────────────────────────────────────── */
  @keyframes shimmer {{
    0%   {{ background-position: -600px 0; }}
    100% {{ background-position:  600px 0; }}
  }}
  .skeleton {{
    background: linear-gradient(
      90deg,
      rgba(255,255,255,0.04) 25%,
      rgba(255,255,255,0.09) 50%,
      rgba(255,255,255,0.04) 75%
    );
    background-size: 600px 100%;
    animation: shimmer 1.4s ease-in-out infinite;
    border-radius: {ra.sm};
    margin-bottom: 8px;
  }}

  /* ── Responsive — tablet (≤ {bp.tablet_max}px) ───────────────────── */
  @media (max-width: {bp.tablet_max}px) {{
    .block-container {{
      max-width: 100% !important;
      padding-left: 1rem !important;
      padding-right: 1rem !important;
    }}
    section[data-testid="stSidebar"] {{
      width: 220px !important;
      min-width: 220px !important;
      max-width: 220px !important;
    }}
    .kpi-card {{ padding: 14px 16px; }}
    .kpi-card .value {{ font-size: 1.4rem; }}
    /* Wrap KPI columns: mínimo 48% para que quepan de 2 en 2 */
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
      min-width: 48% !important;
    }}
  }}

  /* ── Responsive — mobile (≤ {bp.mobile_max}px) ───────────────────── */
  @media (max-width: {bp.mobile_max}px) {{
    .block-container {{
      padding-left: 0.5rem !important;
      padding-right: 0.5rem !important;
    }}
    /* Stack vertical: cada columna ocupa 100% */
    [data-testid="stHorizontalBlock"] {{
      flex-wrap: wrap !important;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
      flex: 1 1 100% !important;
      min-width: 100% !important;
    }}
    /* Reducir tamaño de charts en mobile */
    .js-plotly-plot {{ max-height: 380px !important; }}
    .kpi-card .value {{ font-size: 1.25rem; }}
    h1 {{ font-size: 1.15rem !important; }}
    .bc {{ font-size: 0.72rem; }}
    .top-card .amount {{ font-size: 1.05rem; }}
  }}

  /* ── Focus visible — accesibilidad WCAG AA ─────────────────────────── */
  *:focus-visible {{
    outline: 2px solid {c.accent_primary};
    outline-offset: 2px;
  }}

  /* ── Skip-to-content ──────────────────────────────────────────────── */
  .skip-link {{
    position: absolute;
    left: -9999px;
    top: auto;
    width: 1px;
    height: 1px;
    overflow: hidden;
    z-index: 9999;
    padding: 0.75rem 1.5rem;
    background: {c.accent_primary};
    color: {c.bg_base};
    font-weight: {ty.weight_semibold};
    border-radius: {ra.sm};
    text-decoration: none;
  }}
  .skip-link:focus {{
    left: 1rem;
    top: 0.5rem;
    width: auto;
    height: auto;
    overflow: visible;
  }}

  /* ── prefers-reduced-motion ───────────────────────────────────────── */
  @media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
      animation-duration: 0.001s !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.001s !important;
    }}
  }}
</style>
"""
