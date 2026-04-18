"""Componentes de tarjeta — top_card para licitaciones y adjudicaciones."""
from __future__ import annotations

import html as _html

import streamlit as st

from dashboard.utils.security import safe_url


def top_card(
    amount: str,
    title: str,
    meta: str,
    *,
    url: str | None = None,
    raw_meta: bool = False,
) -> None:
    """Renderiza una top-card con importe, título enlazado y metadatos.

    Args:
        amount: Texto del importe (ya formateado, e.g. "1.23 M€").
        title: Título de la licitación (se escapa y trunca a 120 chars).
        meta: Línea de metadatos. Si `raw_meta=True` se inserta sin escapar
              (útil cuando el caller ya construyó HTML con <b>).
        url: URL de la licitación. Se valida con safe_url.
        raw_meta: Si True, `meta` se inserta como HTML sin escapar.
    """
    href = safe_url(url)
    safe_title = _html.escape(str(title)[:120])
    meta_html = meta if raw_meta else _html.escape(str(meta))

    st.markdown(
        f'<div class="top-card">'
        f'<div class="amount">{_html.escape(amount)}</div>'
        f'<div class="title">'
        f'<a href="{href}" target="_blank" style="color:#E0E0E0;text-decoration:none">'
        f"{safe_title}</a></div>"
        f'<div class="meta">{meta_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
