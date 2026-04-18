"""Carga y enriquecimiento de datos desde SQLite, con caché Streamlit."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from db.database import connect
from dashboard.classifiers import (
    cpv_label,
    detect_modules,
    detect_project_type,
    estado_label,
    nuts_to_ccaa,
    tipo_contrato_label,
)
from dashboard.normalize import normalize_company, normalize_nif


@st.cache_data(ttl=300, show_spinner="Cargando datos…")
def load_dataframe() -> pd.DataFrame:
    with connect() as c:
        cursor = c.execute("SELECT * FROM licitaciones")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["fecha_publicacion"] = pd.to_datetime(
        df["fecha_publicacion"], errors="coerce", utc=True,
    )
    df["importe"] = pd.to_numeric(df["importe"], errors="coerce")
    df["mes"] = df["fecha_publicacion"].dt.to_period("M").dt.to_timestamp()
    df["anyo"] = df["fecha_publicacion"].dt.year

    # Enriquecimiento (clasificadores)
    text_blob = (df["titulo"].fillna("") + " " +
                 df["descripcion"].fillna(""))
    df["modulos"] = text_blob.apply(detect_modules)
    df["modulos_str"] = df["modulos"].apply(lambda l: ", ".join(l))
    df["tipo_proyecto"] = text_blob.apply(detect_project_type)
    df["cpv_desc"] = df["cpv"].apply(cpv_label)
    df["estado_desc"] = df["estado"].apply(estado_label)
    df["tipo_contrato_desc"] = df["tipo_contrato"].apply(tipo_contrato_label)

    # Para registros antiguos sin ccaa pero con nuts, calcular en runtime
    if "ccaa" in df.columns:
        mask = df["ccaa"].isna() & df["nuts_code"].notna()
        df.loc[mask, "ccaa"] = df.loc[mask, "nuts_code"].apply(nuts_to_ccaa)

    return df


@st.cache_data(ttl=300, show_spinner="Cargando adjudicaciones…")
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

    df["fecha_adjudicacion"] = pd.to_datetime(
        df["fecha_adjudicacion"], errors="coerce")
    df["fecha_publicacion"] = pd.to_datetime(
        df["fecha_publicacion"], errors="coerce", utc=True)
    for col in ("importe_adjudicado", "importe_pagable",
                 "oferta_minima", "oferta_maxima", "importe_licitacion"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # % baja del adjudicatario (licitación → adjudicación)
    df["baja_pct"] = ((1 - df["importe_adjudicado"] / df["importe_licitacion"])
                       * 100).where(
        (df["importe_licitacion"] > 0) & df["importe_adjudicado"].notna())

    if "ccaa" in df.columns:
        mask = df["ccaa"].isna() & df["nuts_code"].notna()
        df.loc[mask, "ccaa"] = df.loc[mask, "nuts_code"].apply(nuts_to_ccaa)

    # Detectar UTEs por nombre
    df["es_ute"] = df["nombre"].str.contains(
        r"\bU\.?T\.?E\.?\b", case=False, na=False, regex=True)

    # Normalización para deduplicar
    df["nombre_norm"] = df["nombre"].apply(normalize_company)
    df["nif_norm"] = df["nif"].apply(normalize_nif)
    # empresa_key: prioridad NIF normalizado; fallback nombre normalizado
    df["empresa_key"] = df["nif_norm"].where(
        df["nif_norm"].notna() & (df["nif_norm"] != ""),
        df["nombre_norm"])

    # Nombre canónico = el más frecuente dentro de cada empresa_key
    canon = (df.dropna(subset=["empresa_key"])
                .groupby("empresa_key")["nombre"]
                .agg(lambda s: s.value_counts().index[0])
                .to_dict())
    df["nombre_canonico"] = df["empresa_key"].map(canon).fillna(df["nombre"])
    return df


@st.cache_data(ttl=300)
def load_extracciones() -> pd.DataFrame:
    with connect() as c:
        cursor = c.execute(
            "SELECT * FROM extracciones ORDER BY fecha DESC")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df
