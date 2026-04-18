from __future__ import annotations

import pandas as pd


def fmt_eur(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "—"
    if abs(x) >= 1e9:
        return f"{x/1e9:.2f} B€"
    if abs(x) >= 1e6:
        return f"{x/1e6:.2f} M€"
    if abs(x) >= 1e3:
        return f"{x/1e3:.1f} k€"
    return f"{x:,.0f} €"
