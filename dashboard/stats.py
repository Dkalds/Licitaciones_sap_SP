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
            df["fecha_publicacion"],
            errors="coerce",
            utc=True,
        )
        df["importe"] = pd.to_numeric(df["importe"], errors="coerce")
    return df


def kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total": 0, "importe_total": 0, "importe_medio": 0, "organos": 0}
    return {
        "total": len(df),
        "importe_total": float(df["importe"].sum(skipna=True)),
        "importe_medio": float(df["importe"].mean(skipna=True) or 0),
        "organos": df["organo_contratacion"].nunique(),
    }


def por_mes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df["fecha_publicacion"].isna().all():
        return pd.DataFrame(columns=["mes", "n_licitaciones", "importe"])
    g = (
        df.dropna(subset=["fecha_publicacion"])
        .assign(mes=lambda x: x["fecha_publicacion"].dt.to_period("M").dt.to_timestamp())
        .groupby("mes")
        .agg(n_licitaciones=("id_externo", "count"), importe=("importe", "sum"))
        .reset_index()
    )
    return g


def top_organos(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["organo_contratacion", "n", "importe"])
    g = (
        df.groupby("organo_contratacion")
        .agg(n=("id_externo", "count"), importe=("importe", "sum"))
        .sort_values("n", ascending=False)
        .head(n)
        .reset_index()
    )
    return g


def por_estado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["estado", "n"])
    return df.groupby("estado").size().reset_index(name="n").sort_values("n", ascending=False)


def por_cpv(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["cpv", "n"])
    return df.groupby("cpv").size().reset_index(name="n").sort_values("n", ascending=False).head(n)


# ── Nuevas funciones de KPIs ────────────────────────────────────────────


def yoy_delta(
    df: pd.DataFrame, col: str, agg: str = "count", days: int = 30
) -> tuple[float, float, float]:
    """Calcula valor actual (últimos *days* días), anterior, y % cambio.

    Returns (valor_actual, valor_anterior, pct_cambio).
    """
    hoy = pd.Timestamp.utcnow()
    ult = df[df["fecha_publicacion"] >= (hoy - pd.Timedelta(days=days))]
    prev = df[
        (df["fecha_publicacion"] < (hoy - pd.Timedelta(days=days)))
        & (df["fecha_publicacion"] >= (hoy - pd.Timedelta(days=days * 2)))
    ]

    v_act: float
    v_prev: float
    if agg == "count":
        v_act = float(len(ult))
        v_prev = float(len(prev))
    elif agg == "sum":
        v_act = float(ult[col].sum(skipna=True))
        v_prev = float(prev[col].sum(skipna=True))
    elif agg == "mean":
        v_act = float(ult[col].mean(skipna=True) or 0)
        v_prev = float(prev[col].mean(skipna=True) or 0)
    elif agg == "nunique":
        v_act = float(ult[col].nunique())
        v_prev = float(prev[col].nunique())
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
        rows.append(
            {
                "estado": est,
                "n": n,
                "pct": (n / total * 100) if total else 0,
            }
        )
    return pd.DataFrame(rows)


def hhi_concentracion(adj_df: pd.DataFrame, group_col: str = "empresa_key") -> float:
    """Índice Herfindahl-Hirschman (0-10000) sobre importe adjudicado."""
    if adj_df.empty or "importe_adjudicado" not in adj_df.columns:
        return 0.0
    shares = adj_df.groupby(group_col)["importe_adjudicado"].sum()
    total = shares.sum()
    if total <= 0:
        return 0.0
    pct = shares / total * 100
    return float((pct**2).sum())


def pct_oferta_unica(adj_df: pd.DataFrame) -> float:
    """% de adjudicaciones con una sola oferta recibida."""
    with_data = adj_df.dropna(subset=["n_ofertas_recibidas"])
    if with_data.empty:
        return 0.0
    return float((with_data["n_ofertas_recibidas"] == 1).sum() / len(with_data) * 100)


def media_movil(series: pd.Series, window: int = 3) -> pd.Series:
    """Media móvil simple."""
    return series.rolling(window=window, min_periods=1).mean()


def ventana_anticipacion(df: pd.DataFrame) -> float | None:
    """Días medianos entre publicación y fin de contrato (anticipación comercial).

    Mide cuánto tiempo tiene el equipo comercial desde que sale la licitación
    hasta que el contrato termina. Valores altos = más margen de preparación.
    """
    if df.empty or "fecha_fin_contrato" not in df.columns:
        return None
    fp = pd.to_datetime(df["fecha_publicacion"], errors="coerce", utc=True)
    ff = pd.to_datetime(df["fecha_fin_contrato"], errors="coerce", utc=True)
    if hasattr(fp.dt, "tz"):
        fp = fp.dt.tz_localize(None)
    if hasattr(ff.dt, "tz"):
        ff = ff.dt.tz_localize(None)
    diff = (ff - fp).dt.days
    valid = diff[diff > 0]
    if valid.empty:
        return None
    return float(valid.median())


def indice_novedad(df: pd.DataFrame, df_adj: pd.DataFrame) -> float:
    """% de licitaciones cuyo (órgano, CPV a 2 dígitos) no tiene histórico de adjudicación.

    Útil para identificar "mercados vírgenes" donde aún no hay proveedor instalado.
    """
    if df.empty:
        return 0.0
    df_c = df.copy()
    df_c["_cpv2"] = df_c["cpv"].astype(str).str[:2]

    if df_adj.empty or "licitacion_id" not in df_adj.columns:
        return 100.0  # todo es "nuevo" si no hay histórico

    # Construir set de (órgano, cpv2) con histórico de adjudicación
    hist = df_adj.merge(
        df_c[["id_externo", "organo_contratacion", "_cpv2"]],
        left_on="licitacion_id",
        right_on="id_externo",
        how="inner",
    ).dropna(subset=["organo_contratacion", "_cpv2"])
    if hist.empty:
        return 100.0
    pares_historicos = set(zip(hist["organo_contratacion"], hist["_cpv2"], strict=False))

    # Contar licitaciones cuyo par no aparece en el histórico
    pares_actuales = list(zip(df_c["organo_contratacion"], df_c["_cpv2"], strict=False))
    nuevos = sum(1 for p in pares_actuales if p not in pares_historicos)
    return float(nuevos / len(df_c) * 100)


def ccaa_mas_activa(df: pd.DataFrame) -> dict | None:
    """Devuelve la CCAA con más licitaciones: {ccaa, n, importe}."""
    if df.empty or "ccaa" not in df.columns:
        return None
    geo = (
        df.dropna(subset=["ccaa"])
        .groupby("ccaa")
        .agg(n=("id_externo", "count"), importe=("importe", "sum"))
        .sort_values("n", ascending=False)
    )
    if geo.empty:
        return None
    row = geo.iloc[0]
    return {
        "ccaa": str(geo.index[0]),
        "n": int(row["n"]),
        "importe": float(row["importe"] or 0),
    }


def concentracion_geografica(df: pd.DataFrame, top_n: int = 3) -> float:
    """% del importe total acumulado por las top N CCAA (0-100)."""
    if df.empty or "ccaa" not in df.columns:
        return 0.0
    geo = df.dropna(subset=["ccaa"]).groupby("ccaa")["importe"].sum().sort_values(ascending=False)
    total = geo.sum()
    if total <= 0:
        return 0.0
    return float(geo.head(top_n).sum() / total * 100)


def mes_pico(df: pd.DataFrame) -> dict | None:
    """Mes con mayor volumen acumulado en el rango: {mes: str, importe: float, n: int}."""
    if df.empty or "fecha_publicacion" not in df.columns:
        return None
    mensual = (
        df.dropna(subset=["fecha_publicacion"])
        .assign(_mes=lambda x: x["fecha_publicacion"].dt.to_period("M").dt.to_timestamp())
        .groupby("_mes")
        .agg(n=("id_externo", "count"), importe=("importe", "sum"))
        .sort_values("importe", ascending=False)
    )
    if mensual.empty:
        return None
    row = mensual.iloc[0]
    return {
        "mes": pd.Timestamp(mensual.index[0]).strftime("%b %Y"),
        "importe": float(row["importe"] or 0),
        "n": int(row["n"]),
    }


def ratio_relicitacion(df_pipeline: pd.DataFrame, df_adj: pd.DataFrame) -> float:
    """% de oportunidades del pipeline que vienen de un contrato ya adjudicado (re-licitación).

    Identifica qué proporción son contratos con ganador previo conocido
    (oportunidades de "arrebatar" clientes vs "virgen").
    """
    if df_pipeline.empty:
        return 0.0
    if df_adj.empty or "licitacion_id" not in df_adj.columns:
        return 0.0
    ids_con_adj = set(df_adj["licitacion_id"].dropna())
    if "id_externo" not in df_pipeline.columns:
        return 0.0
    ids_pipeline = df_pipeline["id_externo"].dropna()
    if ids_pipeline.empty:
        return 0.0
    return float(ids_pipeline.isin(ids_con_adj).sum() / len(ids_pipeline) * 100)


def risk_flags(df_lics: pd.DataFrame, df_adj: pd.DataFrame) -> pd.DataFrame:
    """Calcula flags de riesgo para cada licitación (vectorizado).

    Flags posibles:
    - "🔴 Monopolio"        — órgano adjudica ≥80% al mismo proveedor en ese CPV (2 dígitos)
    - "🟡 Baja competencia" — mediana de ofertas recibidas < 2 en ese CPV
    - "🟠 Alta anulación"   — tasa de anulación del órgano > 25%
    - "🔵 Presupuesto bajo" — importe < percentil 10 del CPV

    Returns:
        DataFrame con columnas: id_externo, riesgo_flags (str), riesgo_score (int).
    """
    if df_lics.empty:
        return pd.DataFrame(columns=["id_externo", "riesgo_flags", "riesgo_score"])

    df = df_lics.copy()
    df["_cpv2"] = df["cpv"].astype(str).str[:2]

    # ── Flag: Alta anulación por órgano ─────────────────────────────────────
    organ_stats = (
        df.groupby("organo_contratacion")
        .agg(total=("id_externo", "count"), anuladas=("estado", lambda s: (s == "ANUL").sum()))
        .reset_index()
    )
    organ_stats["_tasa_anulacion"] = organ_stats["anuladas"] / organ_stats["total"] * 100
    df = df.merge(
        organ_stats[["organo_contratacion", "_tasa_anulacion"]],
        on="organo_contratacion",
        how="left",
    )
    df["_alta_anulacion"] = df["_tasa_anulacion"].fillna(0) > 25

    # ── Flag: Presupuesto bajo (< P10 del CPV a 2 dígitos) ──────────────────
    p10_cpv = df.groupby("_cpv2")["importe"].quantile(0.1).rename("_p10_importe").reset_index()
    df = df.merge(p10_cpv, on="_cpv2", how="left")
    df["_presupuesto_bajo"] = (
        df["importe"].notna() & df["_p10_importe"].notna() & (df["importe"] < df["_p10_importe"])
    )

    # ── Flags basados en adjudicaciones históricas ───────────────────────────
    if not df_adj.empty and "licitacion_id" in df_adj.columns:
        # Seleccionar solo las columnas necesarias para evitar colisiones en merge
        _adj_cols = ["licitacion_id", "empresa_key", "n_ofertas_recibidas"]
        adj_slim = df_adj[[c for c in _adj_cols if c in df_adj.columns]].copy()
        adj = adj_slim.merge(
            df[["id_externo", "_cpv2", "organo_contratacion"]],
            left_on="licitacion_id",
            right_on="id_externo",
            how="left",
        ).dropna(subset=["organo_contratacion", "_cpv2"])

        # Cuota máxima por (órgano, cpv2) — monopolio si ≥ 80%
        emp_counts = (
            adj.groupby(["organo_contratacion", "_cpv2", "empresa_key"])
            .size()
            .rename("_emp_n")
            .reset_index()
        )
        grp_totals = (
            adj.groupby(["organo_contratacion", "_cpv2"]).size().rename("_grp_n").reset_index()
        )
        cuota_df = emp_counts.merge(grp_totals, on=["organo_contratacion", "_cpv2"])
        cuota_df["_cuota"] = cuota_df["_emp_n"] / cuota_df["_grp_n"]
        max_cuota = (
            cuota_df.groupby(["organo_contratacion", "_cpv2"])["_cuota"]
            .max()
            .rename("_max_cuota")
            .reset_index()
        )
        df = df.merge(max_cuota, on=["organo_contratacion", "_cpv2"], how="left")
        df["_monopolio"] = df["_max_cuota"].fillna(0) >= 0.80

        # Mediana de ofertas por cpv2 — baja competencia si < 2
        med_ofertas = (
            adj.groupby("_cpv2")["n_ofertas_recibidas"]
            .median()
            .rename("_med_ofertas")
            .reset_index()
        )
        df = df.merge(med_ofertas, on="_cpv2", how="left")
        df["_baja_competencia"] = df["_med_ofertas"].fillna(99) < 2
    else:
        df["_monopolio"] = False
        df["_baja_competencia"] = False

    # ── Construir cadena de flags ────────────────────────────────────────────
    flag_map = {
        "_monopolio": "🔴 Monopolio",
        "_baja_competencia": "🟡 Baja competencia",
        "_alta_anulacion": "🟠 Alta anulación",
        "_presupuesto_bajo": "🔵 Presupuesto bajo",
    }
    flag_cols = list(flag_map.keys())
    df["riesgo_score"] = df[flag_cols].sum(axis=1).astype(int)
    df["riesgo_flags"] = df[flag_cols].apply(
        lambda row: " · ".join(label for col, label in flag_map.items() if row[col]),
        axis=1,
    )

    return df[["id_externo", "riesgo_flags", "riesgo_score"]]
