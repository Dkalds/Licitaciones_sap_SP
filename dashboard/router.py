"""Configuración de navegación y helpers de routing del dashboard."""

from __future__ import annotations

SECTIONS: dict[str, list[str]] = {
    "Vista General": ["Resumen", "Tendencias", "Detalle"],
    "Mercado": ["Órganos", "Geografía", "Proyectos & Módulos"],
    "Competencia": ["Competidores", "Pipeline & Alertas"],
    "Personal": ["Mi Watchlist"],
    "Ops": ["Observabilidad"],
}

SECTION_ICONS: dict[str, str] = {
    "Vista General": "◈",
    "Mercado": "◉",
    "Competencia": "◆",
    "Personal": "★",
    "Ops": "▤",
}
