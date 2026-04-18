"""Cálculo de estadísticas a partir de la BD."""
from __future__ import annotations

import pandas as pd
from db.database import connect


def load_dataframe() -> pd.DataFrame:
    with connect() as c:
        df = pd.read_sql_query("SELECT * FROM licitaciones", c)
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
