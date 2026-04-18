from __future__ import annotations

from io import BytesIO

import pandas as pd


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    out = BytesIO()
    cols = [c for c in df.columns if c not in ("modulos",)]
    export = df[cols].copy()
    # Excel no soporta tz-aware datetimes
    for c in export.select_dtypes(include=["datetimetz"]).columns:
        export[c] = export[c].dt.tz_localize(None)
    export.to_excel(out, index=False, sheet_name="Licitaciones SAP")
    return out.getvalue()
