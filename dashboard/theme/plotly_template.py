"""Template Plotly premium_dark construido desde los design tokens.

Reemplaza el `_premium` layout definido inline en app.py:138-158.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from dashboard.theme.tokens import TOKENS, Tokens

PLOTLY_TEMPLATE_NAME = "plotly_dark+premium_dark"


def build_plotly_template(t: Tokens = TOKENS) -> go.layout.Template:
    c = t.colors
    ty = t.type
    layout = go.Layout(
        font=dict(family=ty.family_plotly, color=c.text_plot_body, size=ty.size_plot_body),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=c.border_plot,
            linewidth=1,
            tickfont=dict(size=ty.size_plot_axis, color=c.text_plot_axis),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=c.border_plot,
            linewidth=1,
            tickfont=dict(size=ty.size_plot_axis, color=c.text_plot_axis),
        ),
        colorway=list(c.plotly_colorway),
        hoverlabel=dict(
            bgcolor=c.bg_hoverlabel,
            bordercolor=c.border_hoverlabel,
            font=dict(family="Inter", size=ty.size_plot_body, color=c.text_card_title),
        ),
        legend=dict(font=dict(size=ty.size_plot_axis, color=c.text_plot_body)),
    )
    return go.layout.Template(layout=layout)


def register_plotly_template(t: Tokens = TOKENS) -> str:
    """Registra el template en pio.templates y devuelve el nombre completo.

    Debe llamarse una sola vez al arrancar la app.
    """
    pio.templates["premium_dark"] = build_plotly_template(t)
    return PLOTLY_TEMPLATE_NAME


def get_color_sequence(t: Tokens = TOKENS) -> list[str]:
    """Lista para `color_discrete_sequence=...` en px.*."""
    return list(t.colors.plotly_colorway)
