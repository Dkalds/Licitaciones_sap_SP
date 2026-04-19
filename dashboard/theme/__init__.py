"""Sistema de diseño centralizado.

Única fuente de verdad para colores, spacing, tipografía y breakpoints del
dashboard. Se consume desde tres sitios:

- `css.build_css(tokens)` inyectado en Streamlit.
- `plotly_template.build_plotly_template(tokens)` para todos los charts.
- `streamlit_config.main()` regenera `.streamlit/config.toml` (offline).
"""

from dashboard.theme.css import build_css
from dashboard.theme.plotly_template import (
    PLOTLY_TEMPLATE_NAME,
    build_plotly_template,
    get_color_sequence,
    register_plotly_template,
)
from dashboard.theme.tokens import TOKENS, Tokens

__all__ = [
    "PLOTLY_TEMPLATE_NAME",
    "TOKENS",
    "Tokens",
    "build_css",
    "build_plotly_template",
    "get_color_sequence",
    "register_plotly_template",
]
