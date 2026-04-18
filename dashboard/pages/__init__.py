"""Registro de páginas — mapea nombres de pestaña a funciones render."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from dashboard.pages._base import PageContext

from dashboard.pages import (
    competidores,
    detalle,
    geografia,
    organos,
    pipeline_alertas,
    proyectos_modulos,
    resumen,
    tendencias,
)

PAGE_REGISTRY: dict[str, Callable[["PageContext"], None]] = {
    "Resumen": resumen.render,
    "Tendencias": tendencias.render,
    "Órganos": organos.render,
    "Geografía": geografia.render,
    "Proyectos & Módulos": proyectos_modulos.render,
    "Detalle": detalle.render,
    "Competidores": competidores.render,
    "Pipeline & Alertas": pipeline_alertas.render,
}
