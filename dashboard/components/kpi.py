"""Componente KPI card — genera HTML para st.markdown."""
from __future__ import annotations

import html as _html


def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_up: bool = True,
    icon: str = "",
) -> str:
    """Devuelve un string HTML con la tarjeta KPI para `st.markdown(..., unsafe_allow_html=True)`.

    El icono se marca como aria-hidden para que lectores de pantalla lo ignoren.
    El div raíz lleva role+aria-label con el valor completo.
    """
    safe_label = _html.escape(str(label))
    safe_value = _html.escape(str(value))
    aria = f"{safe_label}: {safe_value}"

    delta_html = ""
    if delta:
        cls = "up" if delta_up else "down"
        arrow = "▲" if delta_up else "▼"
        safe_delta = _html.escape(str(delta))
        delta_html = f'<div class="delta {cls}">{arrow} {safe_delta}</div>'

    icon_html = (
        f'<span class="icon" aria-hidden="true">{icon}</span>' if icon else ""
    )

    return (
        f'<div class="kpi-card" role="group" aria-label="{aria}">'
        f"{icon_html}"
        f'<div class="label">{safe_label}</div>'
        f'<div class="value">{safe_value}</div>'
        f"{delta_html}"
        f"</div>"
    )
