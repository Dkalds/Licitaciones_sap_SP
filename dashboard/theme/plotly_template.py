"""Template Plotly premium_dark construido desde los design tokens.

Reemplaza el `_premium` layout definido inline en app.py:138-158.
Endurecido en el refresh visual: tipografía Inter consistente, márgenes
estandarizados, leyenda horizontal arriba, ejes con grid muy sutil,
hoverlabel con borde y separación, y modebar oscuro sin logo.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from dashboard.theme.tokens import TOKENS, Tokens

PLOTLY_TEMPLATE_NAME = "plotly_dark+premium_dark"

# Configuración global recomendada para st.plotly_chart(config=PLOTLY_CONFIG).
PLOTLY_CONFIG: dict = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "autoScale2d",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "toggleSpikelines",
    ],
    "displayModeBar": "hover",
    "responsive": True,
}


def build_plotly_template(t: Tokens = TOKENS) -> go.layout.Template:
    c = t.colors
    ty = t.type
    # Grid muy sutil para no competir con los datos
    grid_color = "rgba(255,255,255,0.05)"
    layout = go.Layout(
        font=dict(family=ty.family_plotly, color=c.text_plot_body, size=ty.size_plot_body),
        title=dict(
            font=dict(family=ty.family_plotly, size=14, color=c.text_card_title),
            x=0.0,
            xanchor="left",
            pad=dict(t=4, b=8),
        ),
        margin=dict(t=48, r=16, b=48, l=56),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True,
            gridcolor=grid_color,
            gridwidth=1,
            zeroline=False,
            linecolor=c.border_plot,
            linewidth=1,
            tickfont=dict(size=ty.size_plot_axis, color=c.text_plot_axis),
            title=dict(font=dict(size=ty.size_plot_body, color=c.text_plot_body)),
            automargin=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=grid_color,
            gridwidth=1,
            zeroline=False,
            linecolor=c.border_plot,
            linewidth=1,
            tickfont=dict(size=ty.size_plot_axis, color=c.text_plot_axis),
            title=dict(font=dict(size=ty.size_plot_body, color=c.text_plot_body)),
            automargin=True,
        ),
        colorway=list(c.plotly_colorway),
        hoverlabel=dict(
            bgcolor=c.bg_hoverlabel,
            bordercolor=c.border_hoverlabel,
            font=dict(family=ty.family_plotly, size=ty.size_plot_body, color=c.text_card_title),
            namelength=-1,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=ty.size_plot_axis, color=c.text_plot_body),
            itemwidth=30,
        ),
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color=c.text_muted,
            activecolor=c.accent_primary,
        ),
        separators=",.",
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
