"""Cálculo de estadísticas a partir de la BD."""
from __future__ import annotations

import pandas as pd
from db.database import connect


def load_dataframe() -> pd.DataFrame:
    with connect() as c:
        cursor = c.execute("SELECT * FROM licitaciones")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["fecha_publicacion"] = pd.to_datetime(
            df["fecha_publicacion"], errors="coerce", utc=True,
        )
        df["importe"] = pd.to_numeric(df["importe"], errors="coerce")
    return df


def kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total": 0, "importe_total": 0,
                "importe_medio": 0, "organos": 0}
    return {
        "total": len(df),
        "importe_total": float(df["importe"].sum(skipna=True)),
        "importe_medio": float(df["importe"].mean(skipna=True) or 0),
        "organos": df["organo_contratacion"].nunique(),
    }


def por_mes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df["fecha_publicacion"].isna().all():
        return pd.DataFrame(columns=["mes", "n_licitaciones", "importe"])
    g = (df.dropna(subset=["fecha_publicacion"])
           .assign(mes=lambda x: x["fecha_publicacion"].dt.to_period("M").dt.to_timestamp())
           .groupby("mes")
           .agg(n_licitaciones=("id_externo", "count"),
                importe=("importe", "sum"))
           .reset_index())
    return g


def top_organos(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["organo_contratacion", "n", "importe"])
    g = (df.groupby("organo_contratacion")
           .agg(n=("id_externo", "count"), importe=("importe", "sum"))
           .sort_values("n", ascending=False)
           .head(n)
           .reset_index())
    return g


def por_estado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["estado", "n"])
    return (df.groupby("estado")
              .size()
              .reset_index(name="n")
              .sort_values("n", ascending=False))


def por_cpv(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["cpv", "n"])
    return (df.groupby("cpv")
              .size()
              .reset_index(name="n")
              .sort_values("n", ascending=False)
              .head(n))


# ── Nuevas funciones de KPIs ────────────────────────────────────────────

def yoy_delta(df: pd.DataFrame, col: str, agg: str = "count",
              days: int = 30) -> tuple[float, float, float]:
    """Calcula valor actual (últimos *days* días), anterior, y % cambio.

    Returns (valor_actual, valor_anterior, pct_cambio).
    """
    hoy = pd.Timestamp.utcnow()
    ult = df[df["fecha_publicacion"] >= (hoy - pd.Timedelta(days=days))]
    prev = df[(df["fecha_publicacion"] < (hoy - pd.Timedelta(days=days))) &
              (df["fecha_publicacion"] >= (hoy - pd.Timedelta(days=days * 2)))]

    if agg == "count":
        v_act = len(ult)
        v_prev = len(prev)
    elif agg == "sum":
        v_act = float(ult[col].sum(skipna=True))
        v_prev = float(prev[col].sum(skipna=True))
    elif agg == "mean":
        v_act = float(ult[col].mean(skipna=True) or 0)
        v_prev = float(prev[col].mean(skipna=True) or 0)
    elif agg == "nunique":
        v_act = ult[col].nunique()
        v_prev = prev[col].nunique()
    else:
        v_act = v_prev = 0

    pct = ((v_act - v_prev) / v_prev * 100) if v_prev else 0
    return v_act, v_prev, pct


def tasa_anulacion(df: pd.DataFrame) -> float:
    """% de licitaciones anuladas sobre el total (últimos 12 meses)."""
    hoy = pd.Timestamp.utcnow()
    ult12 = df[df["fecha_publicacion"] >= (hoy - pd.Timedelta(days=365))]
    if ult12.empty:
        return 0.0
    return float((ult12["estado"] == "ANUL").sum() / len(ult12) * 100)


def lead_time_medio(adj_df: pd.DataFrame) -> float | None:
    """Días promedio desde publicación hasta adjudicación."""
    if adj_df.empty:
        return None
    fp = pd.to_datetime(adj_df["fecha_publicacion"], errors="coerce", utc=True)
    fa = pd.to_datetime(adj_df["fecha_adjudicacion"], errors="coerce")
    # Alinear timezones
    if hasattr(fp.dt, "tz"):
        fp = fp.dt.tz_localize(None)
    diff = (fa - fp).dt.days
    valid = diff[diff > 0]
    if valid.empty:
        return None
    return float(valid.median())


def funnel_estados(df: pd.DataFrame) -> pd.DataFrame:
    """Funnel de conversión por estado del proceso de contratación."""
    order = ["PUB", "EV", "RES", "ADJ", "ANUL"]
    counts = df["estado"].value_counts()
    total = len(df)
    rows = []
    for est in order:
        n = int(counts.get(est, 0))
        rows.append({
            "estado": est,
            "n": n,
            "pct": (n / total * 100) if total else 0,
        })
    return pd.DataFrame(rows)


def hhi_concentracion(adj_df: pd.DataFrame,
                      group_col: str = "empresa_key") -> float:
    """Índice Herfindahl-Hirschman (0-10000) sobre importe adjudicado."""
    if adj_df.empty or "importe_adjudicado" not in adj_df.columns:
        return 0.0
    shares = adj_df.groupby(group_col)["importe_adjudicado"].sum()
    total = shares.sum()
    if total <= 0:
        return 0.0
    pct = shares / total * 100
    return float((pct ** 2).sum())


def pct_oferta_unica(adj_df: pd.DataFrame) -> float:
    """% de adjudicaciones con una sola oferta recibida."""
    with_data = adj_df.dropna(subset=["n_ofertas_recibidas"])
    if with_data.empty:
        return 0.0
    return float(
        (with_data["n_ofertas_recibidas"] == 1).sum() /
        len(with_data) * 100
    )


def media_movil(series: pd.Series, window: int = 3) -> pd.Series:
    """Media móvil simple."""
    return series.rolling(window=window, min_periods=1).mean()
