"""Componentes de navegación — breadcrumb, sub-nav y filtros activos."""
from __future__ import annotations

import html as _html
from typing import Callable

import streamlit as st

from dashboard.filters.state import FiltersState


def breadcrumb(section: str, page: str) -> None:
    """Renderiza `Sección › Página` en la barra de navegación secundaria."""
    safe_section = _html.escape(section)
    safe_page = _html.escape(page)
    st.markdown(
        f'<nav aria-label="breadcrumb">'
        f'<div class="bc">'
        f'<span class="bc-section">{safe_section}</span>'
        f'<span class="bc-sep" aria-hidden="true">›</span>'
        f'<span class="bc-page" aria-current="page">{safe_page}</span>'
        f"</div></nav>",
        unsafe_allow_html=True,
    )


def sub_nav(pages: list[str], *, key: str) -> str:
    """Radio horizontal para navegar entre sub-páginas de una sección."""
    return st.radio(
        "p",
        pages,
        horizontal=True,
        label_visibility="collapsed",
        key=key,
    )


def active_filters_chips(
    state: FiltersState,
    on_clear: Callable[[str], None] | None = None,
) -> None:
    """Muestra chips con × para cada filtro activo."""
    labels = state.active_labels()
    if not labels:
        return
    cols = st.columns(len(labels) + 1)
    for i, label in enumerate(labels):
        with cols[i]:
            safe = _html.escape(label)
            st.markdown(
                f'<span style="display:inline-block;background:rgba(255,255,255,0.06);'
                f'border:1px solid rgba(255,255,255,0.10);border-radius:999px;'
                f'padding:2px 10px;font-size:0.78rem;color:#E0E0E0;white-space:nowrap">'
                f'{safe}</span>',
                unsafe_allow_html=True,
            )
