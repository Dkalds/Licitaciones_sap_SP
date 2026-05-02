from __future__ import annotations

import csv
from io import BytesIO, StringIO

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


def kpis_snapshot_csv(kpis: dict[str, str], titulo: str = "Snapshot KPIs") -> bytes:
    """Serializa un diccionario {label: valor_formateado} a CSV listo para descargar.

    Añade timestamp y título como metadatos en las primeras filas para que el
    usuario pueda identificar el snapshot al guardarlo en su sistema.

    Args:
        kpis: dict con KPIs ya formateados como strings (ej. "1,234 €", "85%").
        titulo: encabezado del snapshot.

    Returns:
        Bytes UTF-8-BOM (para que Excel lo abra con acentos bien).
    """
    buf = StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([titulo])
    writer.writerow(["Generado", pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M:%S UTC")])
    writer.writerow([])
    writer.writerow(["KPI", "Valor"])
    for label, value in kpis.items():
        writer.writerow([str(label), str(value)])
    # BOM UTF-8 para compatibilidad con Excel
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")
