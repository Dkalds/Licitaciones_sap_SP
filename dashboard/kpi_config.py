"""Configuración central de KPIs — umbrales, fórmulas y metadatos.

Centraliza:
- KPI_THRESHOLDS: umbrales "verde/rojo" para cada métrica.
- KPI_FORMULAS: explicación corta de cada fórmula (renderizada en tooltip).
- SAP_SERVICES_PORTFOLIO: lista configurable de servicios propios para matching.
- S4HANA_KEYWORDS / ECC_KEYWORDS: patrones para detectar proyectos por plataforma.
"""

from __future__ import annotations

# ── Umbrales por métrica ────────────────────────────────────────────────────
# Cada entrada: (low, high) — se considera "bueno" si el valor está en el rango
# deseado (según la interpretación específica descrita en KPI_FORMULAS).
KPI_THRESHOLDS: dict[str, dict[str, float]] = {
    "exito_pipeline": {"ok": 90.0, "warning": 75.0},  # % de runs con status=ok
    "hhi": {"competitivo": 1500.0, "moderado": 2500.0},  # HHI <1500 = competitivo
    "oferta_unica": {"ok": 20.0, "alert": 40.0},  # % menor es mejor
    "concentracion_top10": {"ok": 60.0, "alert": 80.0},  # % menor es mejor
    "concentracion_geo_top3": {"ok": 60.0, "alert": 80.0},
    "pct_pyme": {"ok": 40.0, "alert": 20.0},  # % mayor es mejor
    "anomaly_sigma": {"threshold": 2.0},  # desvío tipado sobre media para flag
}


# ── Fórmulas / tooltips ─────────────────────────────────────────────────────
KPI_FORMULAS: dict[str, str] = {
    "pct_pyme": (
        "% de adjudicaciones donde la empresa ganadora está clasificada como PYME. "
        "Umbral: ≥40% buena salud del ecosistema."
    ),
    "concentracion_top10": (
        "Suma del importe adjudicado de las 10 empresas con más negocio, "
        "dividido por el total adjudicado. Umbral: <60% mercado sano."
    ),
    "ofertas_adj": (
        "Mediana del número de ofertas recibidas por licitación adjudicada. "
        "Más ofertas = más competencia."
    ),
    "lead_time": (
        "Mediana de días entre publicación y adjudicación. Menos días = procesos más ágiles."
    ),
    "hhi": (
        "Índice Herfindahl-Hirschman = Σ (cuota_i)² sobre importe adjudicado. "
        "<1500 competitivo · 1500-2500 moderado · >2500 concentrado."
    ),
    "oferta_unica": (
        "% de adjudicaciones con una sola oferta recibida. Umbral: <20% ecosistema competitivo."
    ),
    "licitaciones_30d": "Nº de licitaciones publicadas en los últimos 30 días.",
    "importe_30d": "Suma de importes de licitaciones publicadas en los últimos 30 días.",
    "yoy_365d": ("Crecimiento YoY: (ultimos 12m - 12m anteriores) / 12m anteriores * 100."),
    "mes_pico": "Mes con mayor importe acumulado en el rango filtrado actual.",
    "ccaa_activa": "CCAA con más licitaciones en el rango filtrado.",
    "ccaa_ticket": "CCAA con mayor importe medio por licitación (mínimo 5 lics).",
    "concentracion_geo_top3": ("% del importe total acumulado por las 3 CCAA más grandes."),
    "riesgo_alto": "Oportunidades con ≥2 flags de riesgo activos simultáneamente.",
    "pct_importe_riesgo": "% del importe total que tiene al menos 1 flag de riesgo.",
    "relicitacion": ("% de oportunidades del pipeline que vienen de un contrato ya adjudicado."),
    "importe_medio_modulo": "Importe medio por licitación que incluye el módulo SAP.",
    "top_modulo_yoy": ("Módulo SAP con mayor crecimiento YoY (últimos 12m vs 12m anteriores)."),
    "pct_multi_modulo": (
        "% de licitaciones con ≥2 módulos SAP detectados — indican proyectos "
        "integrales / cross-sell."
    ),
    "ticket_s4hana": ("Importe medio de licitaciones mencionando S/4HANA en título/descripción."),
    "portfolio_match": (
        "% del pipeline que encaja con al menos uno de los servicios "
        "configurados en SAP_SERVICES_PORTFOLIO."
    ),
    "calientes_hoy": (
        "Licitaciones en plazo, importe > P75, con ≤1 flag de riesgo y match con watchlist."
    ),
    "vencen_48h": "Oportunidades cuya ventana de decisión termina en las próximas 48h.",
    "velocity_funnel": "Días medianos que tarda una licitación en cada estado.",
    "tasa_conversion_organo": (
        "% de licitaciones de un órgano que acaban en estado ADJ (adjudicadas)."
    ),
    "calidad_cpv": "% de licitaciones con código CPV válido (≥8 dígitos).",
    "calidad_importe": "% de licitaciones con campo importe presente.",
    "calidad_fechas": "% de licitaciones con fecha de publicación válida.",
    "calidad_geo": "% de órganos con coordenadas geográficas resueltas.",
    "antiguedad_scrape": "Horas desde el último run exitoso del scraper.",
}


# ── Portfolio de servicios propios (configurable) ───────────────────────────
# Palabras clave que describen los servicios que ofrece el usuario.
# Si un título o descripción de licitación contiene alguna → "match portfolio".
SAP_SERVICES_PORTFOLIO: list[str] = [
    "implementación",
    "implementacion",
    "migración",
    "migracion",
    "s/4hana",
    "s4hana",
    "rise",
    "mantenimiento",
    "soporte",
    "consultoría",
    "consultoria",
    "desarrollo",
    "integración",
    "integracion",
]


# ── Detección S/4HANA vs ECC ────────────────────────────────────────────────
S4HANA_KEYWORDS: list[str] = ["s/4hana", "s4hana", "s/4 hana", "rise with sap"]
ECC_KEYWORDS: list[str] = ["ecc", "r/3", "sap ecc", "erp 6.0"]
