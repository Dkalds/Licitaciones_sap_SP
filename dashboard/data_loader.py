"""Carga y enriquecimiento de datos desde SQLite, con caché Streamlit."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import DASHBOARD_CACHE_TTL
from db.database import connect, init_db

init_db()
from dashboard.classifiers import (  # noqa: E402
    cpv_label,
    detect_modules,
    detect_project_type,
    estado_label,
    nuts_to_ccaa,
    tipo_contrato_label,
)
from dashboard.normalize import normalize_company, normalize_nif  # noqa: E402


@st.cache_resource(ttl=DASHBOARD_CACHE_TTL or None)
def _load_dataframe_shared() -> pd.DataFrame:
    """Carga base compartida entre todas las sesiones (no copiar)."""
    with connect() as c:
        cursor = c.execute("SELECT * FROM licitaciones")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["fecha_publicacion"] = pd.to_datetime(
        df["fecha_publicacion"],
        errors="coerce",
        utc=True,
    )
    df["importe"] = pd.to_numeric(df["importe"], errors="coerce")
    df["mes"] = df["fecha_publicacion"].dt.to_period("M").dt.to_timestamp()
    df["anyo"] = df["fecha_publicacion"].dt.year

    text_blob = df["titulo"].fillna("") + " " + df["descripcion"].fillna("")
    df["modulos"] = text_blob.apply(detect_modules)
    df["modulos_str"] = df["modulos"].apply(lambda mods: ", ".join(mods))
    df["tipo_proyecto"] = text_blob.apply(detect_project_type)
    df["cpv_desc"] = df["cpv"].apply(cpv_label)
    df["estado_desc"] = df["estado"].apply(estado_label)
    df["tipo_contrato_desc"] = df["tipo_contrato"].apply(tipo_contrato_label)

    if "ccaa" in df.columns:
        mask = df["ccaa"].isna() & df["nuts_code"].notna()
        df.loc[mask, "ccaa"] = df.loc[mask, "nuts_code"].apply(nuts_to_ccaa)

    return df


def load_dataframe() -> pd.DataFrame:
    """Devuelve una copia del DataFrame base (segura para mutaciones por sesión)."""
    return _load_dataframe_shared().copy()


@st.cache_data(ttl=DASHBOARD_CACHE_TTL or None, show_spinner="Cargando adjudicaciones…")
def load_adjudicaciones() -> pd.DataFrame:
    with connect() as c:
        cursor = c.execute(
            "SELECT a.*, l.titulo, l.organo_contratacion, l.url AS url_lic, "
            "       l.fecha_publicacion, l.descripcion AS descripcion_lic, "
            "       l.importe AS importe_licitacion "
            "FROM adjudicaciones a "
            "LEFT JOIN licitaciones l ON l.id_externo = a.licitacion_id",
        )
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["fecha_adjudicacion"] = pd.to_datetime(df["fecha_adjudicacion"], errors="coerce")
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"], errors="coerce", utc=True)
    for col in (
        "importe_adjudicado",
        "importe_pagable",
        "oferta_minima",
        "oferta_maxima",
        "importe_licitacion",
    ):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["baja_pct"] = ((1 - df["importe_adjudicado"] / df["importe_licitacion"]) * 100).where(
        (df["importe_licitacion"] > 0) & df["importe_adjudicado"].notna()
    )

    _fp = df["fecha_publicacion"]
    if hasattr(_fp.dt, "tz") and _fp.dt.tz is not None:
        _fp = _fp.dt.tz_localize(None)
    df["lead_time_dias"] = (df["fecha_adjudicacion"] - _fp).dt.days
    df.loc[df["lead_time_dias"] <= 0, "lead_time_dias"] = pd.NA

    if "ccaa" in df.columns:
        mask = df["ccaa"].isna() & df["nuts_code"].notna()
        df.loc[mask, "ccaa"] = df.loc[mask, "nuts_code"].apply(nuts_to_ccaa)

    df["es_ute"] = df["nombre"].str.contains(r"\bU\.?T\.?E\.?\b", case=False, na=False, regex=True)

    df["nombre_norm"] = df["nombre"].apply(normalize_company)
    df["nif_norm"] = df["nif"].apply(normalize_nif)
    df["empresa_key"] = df["nif_norm"].where(
        df["nif_norm"].notna() & (df["nif_norm"] != ""), df["nombre_norm"]
    )

    canon = (
        df.dropna(subset=["empresa_key"])
        .groupby("empresa_key")["nombre"]
        .agg(lambda s: s.value_counts().index[0])
        .to_dict()
    )
    df["nombre_canonico"] = df["empresa_key"].map(canon).fillna(df["nombre"])
    return df


@st.cache_data(ttl=DASHBOARD_CACHE_TTL or None)
def load_extracciones() -> pd.DataFrame:
    with connect() as c:
        cursor = c.execute("SELECT * FROM extracciones ORDER BY fecha DESC")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df


def invalidate_caches() -> None:
    """Fuerza recarga de todas las fuentes cacheadas en la próxima llamada."""
    _load_dataframe_shared.clear()
    load_adjudicaciones.clear()
    load_extracciones.clear()
