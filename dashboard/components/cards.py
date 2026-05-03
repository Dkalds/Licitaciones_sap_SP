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
    highlight: str | None = None,
) -> None:
    """Renderiza una top-card con importe, título enlazado y metadatos.

    Args:
        amount: Texto del importe (ya formateado, e.g. "1.23 M€").
        title: Título de la licitación (se escapa y trunca a 120 chars).
        meta: Línea de metadatos. Siempre se escapa automáticamente.
        url: URL de la licitación. Se valida con safe_url.
        highlight: Si se proporciona, se añade en negrita al final del meta
                   (también escapado automáticamente).
    """
    href = safe_url(url)
    safe_title = _html.escape(str(title)[:120])
    meta_escaped = _html.escape(str(meta))
    if highlight is not None:
        meta_html = f"{meta_escaped} · <b>{_html.escape(str(highlight))}</b>"
    else:
        meta_html = meta_escaped

    st.markdown(
        f'<div class="top-card">'
        f'<div class="amount">{_html.escape(amount)}</div>'
        f'<div class="title">'
        f'<a href="{href}" target="_blank">'
        f"{safe_title}</a></div>"
        f'<div class="meta">{meta_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
