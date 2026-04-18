"""Base para el sistema de páginas — PageContext y helpers."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from dashboard.filters.state import FiltersState
from dashboard.theme.tokens import Tokens


@dataclass
class PageContext:
    """Contexto inyectado a cada página por el router de app.py."""

    df: pd.DataFrame
    df_full: pd.DataFrame
    filters: FiltersState
    tokens: Tokens
    plotly_template: str
    color_sequence: list[str]
