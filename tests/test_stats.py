"""Tests para dashboard/stats.py — funciones de estadísticas puras."""

from __future__ import annotations

import pandas as pd
import pytest

from dashboard.stats import (
    calidad_dato,
    calientes_hoy,
    ccaa_mas_activa,
    concentracion_geografica,
    funnel_estados,
    hhi_concentracion,
    importe_medio_por_modulo,
    indice_novedad,
    is_anomaly,
    kpi_sparkline_series,
    kpis,
    lead_time_medio,
    media_movil,
    mes_pico,
    pct_multi_modulo,
    pct_oferta_unica,
    por_cpv,
    por_estado,
    por_mes,
    portfolio_match,
    ratio_relicitacion,
    risk_flags,
    score_oportunidad,
    tasa_anulacion,
    tasa_conversion_organo,
    ticket_medio_por_plataforma,
    top_modulo_yoy,
    top_organos,
    velocity_funnel,
    vencen_en,
    ventana_anticipacion,
    yoy_delta,
)

# ─── helpers ────────────────────────────────────────────────────────────────


def _base_df(n: int = 5) -> pd.DataFrame:
    """DataFrame mínimo compatible con todas las funciones."""
    now = pd.Timestamp.utcnow()
    return pd.DataFrame(
        {
            "id_externo": [f"id-{i}" for i in range(n)],
            "fecha_publicacion": [now - pd.Timedelta(days=i * 10) for i in range(n)],
            "importe": [1000.0 * (i + 1) for i in range(n)],
            "organo_contratacion": [f"Org-{i % 2}" for i in range(n)],
            "ccaa": [f"CCAA-{i % 3}" for i in range(n)],
            "cpv": [f"72{i}0000" for i in range(n)],
            "estado": ["PUB", "EV", "RES", "ADJ", "ANUL"][:n] if n <= 5 else ["PUB"] * n,
        }
    )


def _empty_df() -> pd.DataFrame:
    cols = [
        "id_externo",
        "fecha_publicacion",
        "importe",
        "organo_contratacion",
        "ccaa",
        "cpv",
        "estado",
    ]
    df = pd.DataFrame(columns=cols)
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"], utc=True)
    df["importe"] = pd.to_numeric(df["importe"])
    return df


# ─── kpis ────────────────────────────────────────────────────────────────────


class TestKpis:
    def test_empty_returns_zeros(self):
        k = kpis(_empty_df())
        assert k == {"total": 0, "importe_total": 0, "importe_medio": 0, "organos": 0}

    def test_non_empty_totals(self):
        df = _base_df(4)
        k = kpis(df)
        assert k["total"] == 4
        assert k["importe_total"] == pytest.approx(1000 + 2000 + 3000 + 4000)
        assert k["importe_medio"] == pytest.approx(2500.0)
        assert k["organos"] == 2


# ─── por_mes ─────────────────────────────────────────────────────────────────


class TestPorMes:
    def test_empty_returns_empty_df(self):
        result = por_mes(_empty_df())
        assert list(result.columns) == ["mes", "n_licitaciones", "importe"]
        assert result.empty

    def test_groups_by_month(self):
        df = _base_df(5)
        result = por_mes(df)
        assert "mes" in result.columns
        assert "n_licitaciones" in result.columns
        assert result["n_licitaciones"].sum() == 5

    def test_all_nat_returns_empty(self):
        df = _base_df(3)
        df["fecha_publicacion"] = pd.NaT
        result = por_mes(df)
        assert result.empty


# ─── top_organos ─────────────────────────────────────────────────────────────


class TestTopOrganos:
    def test_empty_returns_empty_df(self):
        result = top_organos(_empty_df())
        assert result.empty

    def test_returns_correct_columns(self):
        df = _base_df(5)
        result = top_organos(df, n=2)
        assert "organo_contratacion" in result.columns
        assert "n" in result.columns
        assert len(result) <= 2

    def test_sorted_descending(self):
        df = _base_df(5)
        result = top_organos(df)
        if len(result) >= 2:
            assert result.iloc[0]["n"] >= result.iloc[1]["n"]


# ─── por_estado ──────────────────────────────────────────────────────────────


class TestPorEstado:
    def test_empty_returns_empty_df(self):
        result = por_estado(_empty_df())
        assert result.empty

    def test_counts_correctly(self):
        df = _base_df(5)  # one each: PUB, EV, RES, ADJ, ANUL
        result = por_estado(df)
        assert len(result) == 5
        assert result["n"].sum() == 5


# ─── por_cpv ─────────────────────────────────────────────────────────────────


class TestPorCpv:
    def test_empty_returns_empty_df(self):
        result = por_cpv(_empty_df())
        assert result.empty

    def test_top_n_limit(self):
        df = _base_df(5)
        result = por_cpv(df, n=3)
        assert len(result) <= 3


# ─── yoy_delta ───────────────────────────────────────────────────────────────


class TestYoyDelta:
    def _build(self) -> pd.DataFrame:
        now = pd.Timestamp.utcnow()
        rows = []
        # 5 en últimos 30 días
        for i in range(5):
            rows.append(
                {
                    "id_externo": f"r{i}",
                    "fecha_publicacion": now - pd.Timedelta(days=i + 1),
                    "importe": 1000.0,
                    "organo_contratacion": "Org",
                    "ccaa": "Mad",
                    "cpv": "72",
                    "estado": "PUB",
                }
            )
        # 3 en período anterior (30-60 días)
        for i in range(3):
            rows.append(
                {
                    "id_externo": f"p{i}",
                    "fecha_publicacion": now - pd.Timedelta(days=35 + i),
                    "importe": 500.0,
                    "organo_contratacion": "Org",
                    "ccaa": "Mad",
                    "cpv": "72",
                    "estado": "PUB",
                }
            )
        return pd.DataFrame(rows)

    def test_count_agg(self):
        df = self._build()
        v_act, v_prev, pct = yoy_delta(df, col="importe", agg="count")
        assert v_act == 5
        assert v_prev == 3
        assert pct == pytest.approx((5 - 3) / 3 * 100, rel=1e-3)

    def test_sum_agg(self):
        df = self._build()
        v_act, v_prev, _pct = yoy_delta(df, col="importe", agg="sum")
        assert v_act == pytest.approx(5000.0)
        assert v_prev == pytest.approx(1500.0)

    def test_mean_agg(self):
        df = self._build()
        v_act, _v_prev, _ = yoy_delta(df, col="importe", agg="mean")
        assert v_act == pytest.approx(1000.0)

    def test_nunique_agg(self):
        df = self._build()
        v_act, _, _ = yoy_delta(df, col="ccaa", agg="nunique")
        assert v_act == 1

    def test_unknown_agg_returns_zeros(self):
        df = self._build()
        v_act, v_prev, pct = yoy_delta(df, col="importe", agg="unknown_agg")
        assert v_act == 0
        assert v_prev == 0
        assert pct == 0

    def test_no_prev_period_returns_pct_zero(self):
        """Si prev == 0, pct debe ser 0 (sin división por cero)."""
        now = pd.Timestamp.utcnow()
        df = pd.DataFrame(
            [
                {
                    "id_externo": "x1",
                    "fecha_publicacion": now - pd.Timedelta(days=1),
                    "importe": 100.0,
                    "organo_contratacion": "O",
                    "ccaa": "C",
                    "cpv": "72",
                    "estado": "PUB",
                }
            ]
        )
        _v_act, v_prev, pct = yoy_delta(df, col="importe", agg="count")
        assert v_prev == 0
        assert pct == 0


# ─── tasa_anulacion ──────────────────────────────────────────────────────────


class TestTasaAnulacion:
    def test_empty_returns_zero(self):
        assert tasa_anulacion(_empty_df()) == 0.0

    def test_no_anuladas_returns_zero(self):
        df = _base_df(4)
        df["estado"] = "PUB"
        assert tasa_anulacion(df) == 0.0

    def test_all_anuladas_returns_100(self):
        now = pd.Timestamp.utcnow()
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b"],
                "fecha_publicacion": [now - pd.Timedelta(days=10), now - pd.Timedelta(days=20)],
                "importe": [1000.0, 2000.0],
                "organo_contratacion": ["O", "O"],
                "ccaa": ["C", "C"],
                "cpv": ["72", "72"],
                "estado": ["ANUL", "ANUL"],
            }
        )
        assert tasa_anulacion(df) == pytest.approx(100.0)

    def test_partial_rate(self):
        now = pd.Timestamp.utcnow()
        rows = []
        for i in range(4):
            rows.append(
                {
                    "id_externo": f"x{i}",
                    "fecha_publicacion": now - pd.Timedelta(days=i + 1),
                    "importe": 1000.0,
                    "organo_contratacion": "O",
                    "ccaa": "C",
                    "cpv": "72",
                    "estado": "ANUL" if i < 1 else "PUB",
                }
            )
        df = pd.DataFrame(rows)
        rate = tasa_anulacion(df)
        assert rate == pytest.approx(25.0)

    def test_records_outside_12_months_excluded(self):
        now = pd.Timestamp.utcnow()
        df = pd.DataFrame(
            {
                "id_externo": ["old"],
                "fecha_publicacion": [now - pd.Timedelta(days=400)],
                "importe": [1000.0],
                "organo_contratacion": ["O"],
                "ccaa": ["C"],
                "cpv": ["72"],
                "estado": ["ANUL"],
            }
        )
        # Debe quedar fuera del año y por tanto retornar 0
        assert tasa_anulacion(df) == 0.0


# ─── lead_time_medio ─────────────────────────────────────────────────────────


class TestLeadTimeMedio:
    def test_empty_returns_none(self):
        assert lead_time_medio(pd.DataFrame()) is None

    def test_returns_median_positive_days(self):
        df = pd.DataFrame(
            {
                "fecha_publicacion": ["2024-01-01", "2024-01-01"],
                "fecha_adjudicacion": ["2024-04-01", "2024-07-01"],
            }
        )
        result = lead_time_medio(df)
        assert result is not None
        assert result > 0

    def test_negative_days_excluded(self):
        df = pd.DataFrame(
            {
                "fecha_publicacion": ["2024-06-01"],
                "fecha_adjudicacion": ["2024-01-01"],  # adjudicado ANTES de publicado
            }
        )
        result = lead_time_medio(df)
        assert result is None  # no hay días válidos > 0


# ─── funnel_estados ──────────────────────────────────────────────────────────


class TestFunnelEstados:
    def test_returns_all_order_rows(self):
        df = _base_df(5)
        result = funnel_estados(df)
        assert len(result) == 5  # PUB, EV, RES, ADJ, ANUL
        assert list(result["estado"]) == ["PUB", "EV", "RES", "ADJ", "ANUL"]

    def test_missing_estado_shows_zero(self):
        df = pd.DataFrame({"estado": ["PUB", "PUB", "PUB"]})
        result = funnel_estados(df)
        pub_row = result[result["estado"] == "PUB"]
        assert int(pub_row["n"].iloc[0]) == 3
        ev_row = result[result["estado"] == "EV"]
        assert int(ev_row["n"].iloc[0]) == 0

    def test_pct_sums_to_100_when_all_represented(self):
        df = _base_df(5)
        result = funnel_estados(df)
        assert result["pct"].sum() == pytest.approx(100.0)


# ─── hhi_concentracion ───────────────────────────────────────────────────────


class TestHhiConcentracion:
    def test_empty_returns_zero(self):
        assert hhi_concentracion(pd.DataFrame()) == 0.0

    def test_monopolio_cerca_de_10000(self):
        df = pd.DataFrame(
            {
                "empresa_key": ["emp_a"],
                "importe_adjudicado": [1_000_000.0],
            }
        )
        result = hhi_concentracion(df)
        assert result == pytest.approx(10000.0, rel=1e-3)

    def test_dos_iguales_son_5000(self):
        df = pd.DataFrame(
            {
                "empresa_key": ["a", "b"],
                "importe_adjudicado": [500_000.0, 500_000.0],
            }
        )
        result = hhi_concentracion(df)
        assert result == pytest.approx(5000.0, rel=1e-3)

    def test_sin_columna_importe_adjudicado_returns_zero(self):
        df = pd.DataFrame({"empresa_key": ["a"], "importe": [100.0]})
        assert hhi_concentracion(df) == 0.0

    def test_total_cero_returns_zero(self):
        df = pd.DataFrame(
            {
                "empresa_key": ["a"],
                "importe_adjudicado": [0.0],
            }
        )
        assert hhi_concentracion(df) == 0.0


# ─── pct_oferta_unica ────────────────────────────────────────────────────────


class TestPctOfertaUnica:
    def test_empty_after_dropna_returns_zero(self):
        df = pd.DataFrame({"n_ofertas_recibidas": [None, None]})
        assert pct_oferta_unica(df) == 0.0

    def test_all_single_bids(self):
        df = pd.DataFrame({"n_ofertas_recibidas": [1.0, 1.0, 1.0]})
        assert pct_oferta_unica(df) == pytest.approx(100.0)

    def test_half_single_bids(self):
        df = pd.DataFrame({"n_ofertas_recibidas": [1.0, 2.0, 1.0, 3.0]})
        assert pct_oferta_unica(df) == pytest.approx(50.0)


# ─── media_movil ─────────────────────────────────────────────────────────────


class TestMediaMovil:
    def test_window_3(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = media_movil(s, window=3)
        # Valores: 1, 1.5, 2, 3, 4
        assert result.iloc[-1] == pytest.approx(4.0)

    def test_min_periods_1(self):
        s = pd.Series([10.0, 20.0])
        result = media_movil(s, window=5)
        assert result.iloc[0] == pytest.approx(10.0)  # sólo 1 valor disponible


# ─── risk_flags ──────────────────────────────────────────────────────────────


def _lics_df() -> pd.DataFrame:
    """5 licitaciones con datos suficientes para todos los flags."""
    return pd.DataFrame(
        {
            "id_externo": ["id-1", "id-2", "id-3", "id-4", "id-5"],
            "organo_contratacion": ["OrgA", "OrgA", "OrgB", "OrgB", "OrgC"],
            "cpv": ["7200", "7200", "7200", "7201", "8000"],
            "importe": [100_000.0, 200_000.0, 50_000.0, 1_000.0, 300_000.0],
            "estado": ["PUB", "PUB", "ANUL", "ANUL", "PUB"],
        }
    )


def _adj_df() -> pd.DataFrame:
    """Adjudicaciones con monopolio en OrgA+cpv72 y baja competencia en cpv72."""
    return pd.DataFrame(
        {
            "licitacion_id": ["id-1", "id-2", "id-3"],
            "empresa_key": ["emp_A", "emp_A", "emp_B"],  # emp_A gana 2/2 en OrgA→monopolio
            "n_ofertas_recibidas": [1.0, 1.0, 2.0],  # mediana cpv72 = 1 → baja competencia
            "organo_contratacion": ["OrgA", "OrgA", "OrgB"],
        }
    )


class TestRiskFlags:
    def test_empty_lics_returns_empty(self):
        result = risk_flags(pd.DataFrame(), pd.DataFrame())
        assert result.empty
        assert list(result.columns) == ["id_externo", "riesgo_flags", "riesgo_score"]

    def test_no_adj_returns_no_monopolio_no_baja_competencia(self):
        result = risk_flags(_lics_df(), pd.DataFrame())
        assert "id-1" in result["id_externo"].values
        row = result[result["id_externo"] == "id-1"].iloc[0]
        assert "Monopolio" not in row["riesgo_flags"]
        assert "Baja competencia" not in row["riesgo_flags"]

    def test_monopolio_flag_detected(self):
        result = risk_flags(_lics_df(), _adj_df())
        # id-1 y id-2 están en OrgA con cpv72, donde emp_A tiene cuota 100% → monopolio
        row1 = result[result["id_externo"] == "id-1"].iloc[0]
        assert "Monopolio" in row1["riesgo_flags"]

    def test_baja_competencia_flag_detected(self):
        result = risk_flags(_lics_df(), _adj_df())
        # mediana de n_ofertas en cpv "72" es 1 → baja competencia
        row1 = result[result["id_externo"] == "id-1"].iloc[0]
        assert "Baja competencia" in row1["riesgo_flags"]

    def test_alta_anulacion_flag_detected(self):
        result = risk_flags(_lics_df(), pd.DataFrame())
        # OrgB tiene 2 licitaciones, 2 ANUL → tasa 100% > 25%
        row3 = result[result["id_externo"] == "id-3"].iloc[0]
        assert "Alta anulación" in row3["riesgo_flags"]

    def test_presupuesto_bajo_flag_detected(self):
        result = risk_flags(_lics_df(), pd.DataFrame())
        # id-4 tiene importe 1000, muy por debajo del P10 de su CPV
        row4 = result[result["id_externo"] == "id-4"].iloc[0]
        assert "Presupuesto bajo" in row4["riesgo_flags"]

    def test_score_reflects_flag_count(self):
        result = risk_flags(_lics_df(), _adj_df())
        for _, row in result.iterrows():
            n_flags = len([f for f in row["riesgo_flags"].split(" · ") if f])
            assert row["riesgo_score"] == n_flags

    def test_clean_row_has_empty_flags(self):
        result = risk_flags(_lics_df(), _adj_df())
        # id-5 está en OrgC (0% anulación), CPV "80" sin adj → sin flags
        row5 = result[result["id_externo"] == "id-5"].iloc[0]
        assert row5["riesgo_flags"] == ""
        assert row5["riesgo_score"] == 0


# ─── ventana_anticipacion ────────────────────────────────────────────────────


class TestVentanaAnticipacion:
    def test_empty_returns_none(self):
        assert ventana_anticipacion(pd.DataFrame()) is None

    def test_missing_column_returns_none(self):
        df = pd.DataFrame({"fecha_publicacion": ["2024-01-01"]})
        assert ventana_anticipacion(df) is None

    def test_returns_median_days(self):
        df = pd.DataFrame(
            {
                "fecha_publicacion": ["2024-01-01", "2024-01-01"],
                "fecha_fin_contrato": ["2024-07-01", "2025-01-01"],
            }
        )
        result = ventana_anticipacion(df)
        assert result is not None
        assert result > 0


# ─── indice_novedad ──────────────────────────────────────────────────────────


class TestIndiceNovedad:
    def test_empty_returns_zero(self):
        assert indice_novedad(pd.DataFrame(), pd.DataFrame()) == 0.0

    def test_no_adj_returns_100(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b"],
                "organo_contratacion": ["Org1", "Org2"],
                "cpv": ["72", "73"],
            }
        )
        assert indice_novedad(df, pd.DataFrame()) == 100.0

    def test_half_novedad(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b"],
                "organo_contratacion": ["Org1", "Org2"],
                "cpv": ["7200", "7300"],
            }
        )
        # Solo Org1+cpv72 aparece en histórico → b (Org2+73) es novedad (50%)
        adj = pd.DataFrame(
            {
                "licitacion_id": ["a"],
            }
        )
        result = indice_novedad(df, adj)
        assert result == 50.0


# ─── ccaa_mas_activa / concentracion_geografica / mes_pico ──────────────────


class TestGeoKpis:
    def test_ccaa_mas_activa_empty(self):
        assert ccaa_mas_activa(pd.DataFrame()) is None

    def test_ccaa_mas_activa_picks_top(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b", "c", "d"],
                "ccaa": ["Madrid", "Madrid", "Catalunya", "Madrid"],
                "importe": [100.0, 200.0, 500.0, 100.0],
            }
        )
        result = ccaa_mas_activa(df)
        assert result is not None
        assert result["ccaa"] == "Madrid"
        assert result["n"] == 3

    def test_concentracion_geografica_empty(self):
        assert concentracion_geografica(pd.DataFrame()) == 0.0

    def test_concentracion_geografica_top1_is_100(self):
        df = pd.DataFrame({"ccaa": ["Madrid"], "importe": [1000.0]})
        assert concentracion_geografica(df, top_n=1) == pytest.approx(100.0)

    def test_mes_pico_empty(self):
        assert mes_pico(pd.DataFrame()) is None

    def test_mes_pico_returns_max_importe_month(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b", "c"],
                "fecha_publicacion": pd.to_datetime(["2024-01-15", "2024-02-15", "2024-02-20"]),
                "importe": [100.0, 300.0, 500.0],
            }
        )
        result = mes_pico(df)
        assert result is not None
        assert "Feb" in result["mes"]
        assert result["n"] == 2


# ─── ratio_relicitacion ──────────────────────────────────────────────────────


class TestRatioRelicitacion:
    def test_empty_pipeline_returns_zero(self):
        assert ratio_relicitacion(pd.DataFrame(), pd.DataFrame()) == 0.0

    def test_empty_adj_returns_zero(self):
        df = pd.DataFrame({"id_externo": ["a", "b"]})
        assert ratio_relicitacion(df, pd.DataFrame()) == 0.0

    def test_half_relicitacion(self):
        pipeline = pd.DataFrame({"id_externo": ["a", "b", "c", "d"]})
        adj = pd.DataFrame({"licitacion_id": ["a", "b"]})
        result = ratio_relicitacion(pipeline, adj)
        assert result == 50.0

    def test_all_relicitacion(self):
        pipeline = pd.DataFrame({"id_externo": ["a", "b"]})
        adj = pd.DataFrame({"licitacion_id": ["a", "b", "c"]})
        result = ratio_relicitacion(pipeline, adj)
        assert result == 100.0


# ─── kpi_sparkline_series ───────────────────────────────────────────────────


class TestSparklineSeries:
    def test_empty_df(self):
        assert kpi_sparkline_series(_empty_df()) == []

    def test_returns_list_of_floats(self):
        df = _base_df(8)
        out = kpi_sparkline_series(df, metric="count", freq="W", periods=4)
        assert isinstance(out, list)
        assert all(isinstance(v, float) for v in out)

    def test_sum_metric(self):
        df = _base_df(6)
        out = kpi_sparkline_series(df, metric="sum", freq="ME", periods=6)
        assert len(out) <= 6

    def test_unknown_metric_returns_empty(self):
        df = _base_df(5)
        assert kpi_sparkline_series(df, metric="zzz") == []


# ─── is_anomaly ─────────────────────────────────────────────────────────────


class TestAnomaly:
    def test_not_enough_history(self):
        assert is_anomaly(10.0, [5.0, 7.0]) is False

    def test_no_anomaly_within_range(self):
        history = [10.0, 11.0, 9.0, 10.5, 9.5, 10.2, 10.8, 9.7]
        assert is_anomaly(10.3, history) is False

    def test_anomaly_above_2_sigma(self):
        history = [10.0, 11.0, 9.0, 10.5, 9.5, 10.2, 10.8, 9.7]
        assert is_anomaly(50.0, history) is True

    def test_constant_history_tolerance(self):
        history = [10.0, 10.0, 10.0, 10.0]
        assert is_anomaly(10.0, history) is False
        assert is_anomaly(15.0, history) is True  # >10% desviación


# ─── importe_medio_por_modulo ───────────────────────────────────────────────


class TestImporteMedioModulo:
    def test_empty(self):
        df = _empty_df()
        df["modulos"] = []
        out = importe_medio_por_modulo(df)
        assert out.empty

    def test_groups_by_modulo(self):
        df = _base_df(3).copy()
        df["modulos"] = [["FI", "CO"], ["FI"], ["MM"]]
        out = importe_medio_por_modulo(df)
        assert set(out["modulo"].tolist()) == {"FI", "CO", "MM"}
        fi_row = out[out["modulo"] == "FI"].iloc[0]
        assert fi_row["n"] == 2


# ─── top_modulo_yoy ─────────────────────────────────────────────────────────


class TestTopModuloYoy:
    def test_empty_returns_none(self):
        df = _empty_df()
        df["modulos"] = []
        assert top_modulo_yoy(df) is None

    def test_picks_highest_growth(self):
        hoy = pd.Timestamp.utcnow()
        rows = []
        # 5 lics de FI en los últimos 365d, 1 en 365-730d atrás → crecimiento 400%
        for i in range(5):
            rows.append({"modulos": ["FI"], "fecha_publicacion": hoy - pd.Timedelta(days=30 * i)})
        rows.append({"modulos": ["FI"], "fecha_publicacion": hoy - pd.Timedelta(days=500)})
        # 3 lics de MM solo recientes (año actual) — crecimiento 'NUEVO'
        for i in range(3):
            rows.append({"modulos": ["MM"], "fecha_publicacion": hoy - pd.Timedelta(days=30 * i)})
        df = pd.DataFrame(rows)
        out = top_modulo_yoy(df)
        assert out is not None
        # MM tiene crecimiento infinito (999) así que gana sobre FI (400%)
        assert out["modulo"] == "MM"


# ─── pct_multi_modulo ───────────────────────────────────────────────────────


class TestPctMultiModulo:
    def test_empty_returns_zero(self):
        df = _empty_df()
        df["modulos"] = []
        assert pct_multi_modulo(df) == 0.0

    def test_half_multi(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b", "c", "d"],
                "modulos": [["FI"], ["FI", "CO"], ["MM", "SD", "FI"], ["FI"]],
            }
        )
        # 2 de 4 con ≥2 módulos → 50%
        assert pct_multi_modulo(df) == 50.0


# ─── ticket_medio_por_plataforma ────────────────────────────────────────────


class TestTicketPorPlataforma:
    def test_empty(self):
        out = ticket_medio_por_plataforma(_empty_df())
        assert out["s4hana"]["n"] == 0
        assert out["ecc"]["n"] == 0

    def test_detects_s4hana(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b"],
                "titulo": ["Migración a S/4HANA de la AEAT", "Mantenimiento ECC 6.0"],
                "descripcion": ["", ""],
                "importe": [1_000_000, 500_000],
            }
        )
        out = ticket_medio_por_plataforma(df)
        assert out["s4hana"]["n"] == 1
        assert out["s4hana"]["ticket_medio"] == 1_000_000
        assert out["ecc"]["n"] == 1
        assert out["ecc"]["ticket_medio"] == 500_000


# ─── portfolio_match ────────────────────────────────────────────────────────


class TestPortfolioMatch:
    def test_empty(self):
        assert portfolio_match(_empty_df()) == 0.0

    def test_custom_keywords(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b", "c"],
                "titulo": ["Implementación FI/CO", "Suministro papel", "Migración S/4HANA"],
                "descripcion": ["", "", ""],
            }
        )
        # 2 de 3 contienen palabras clave → ~66.7%
        assert portfolio_match(df) == pytest.approx(100 * 2 / 3, rel=0.01)

    def test_empty_keywords_returns_zero(self):
        df = _base_df(3)
        assert portfolio_match(df, keywords=[]) == 0.0


# ─── calientes_hoy ──────────────────────────────────────────────────────────


class TestCalientesHoy:
    def test_empty_returns_empty(self):
        out = calientes_hoy(_empty_df())
        assert out.empty

    def test_filters_by_estado_and_p75(self):
        hoy = pd.Timestamp.utcnow()
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b", "c", "d"],
                "estado": ["PUB", "PUB", "ADJ", "EV"],
                "importe": [100, 500, 1000, 10000],
                "fecha_publicacion": [hoy] * 4,
                "cpv": ["72000000"] * 4,
                "organo_contratacion": ["Org"] * 4,
            }
        )
        out = calientes_hoy(df)
        # Solo PUB/EV, con importe >= P75. Los PUB/EV son a(100), b(500), d(10000).
        # P75 de [100, 500, 10000] = 5250. Solo "d" pasa.
        assert "d" in out["id_externo"].values
        assert "c" not in out["id_externo"].values  # ADJ excluido


# ─── vencen_en ──────────────────────────────────────────────────────────────


class TestVencenEn:
    def test_empty(self):
        assert vencen_en(_empty_df()) == 0

    def test_count_in_window(self):
        hoy = pd.Timestamp.utcnow()
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b", "c"],
                "fecha_fin_plazo": [
                    hoy + pd.Timedelta(hours=12),  # dentro
                    hoy + pd.Timedelta(hours=30),  # dentro
                    hoy + pd.Timedelta(days=5),  # fuera
                ],
            }
        )
        assert vencen_en(df, horas=48) == 2


# ─── velocity_funnel ────────────────────────────────────────────────────────


class TestVelocityFunnel:
    def test_empty_no_keys(self):
        out = velocity_funnel(_empty_df())
        assert out == {}

    def test_pub_a_fin_plazo(self):
        hoy = pd.Timestamp.utcnow()
        df = pd.DataFrame(
            {
                "fecha_publicacion": [hoy - pd.Timedelta(days=10)] * 3,
                "fecha_fin_plazo": [
                    hoy - pd.Timedelta(days=5),
                    hoy - pd.Timedelta(days=3),
                    hoy - pd.Timedelta(days=1),
                ],
            }
        )
        out = velocity_funnel(df)
        assert "pub_a_fin_plazo" in out


# ─── tasa_conversion_organo ─────────────────────────────────────────────────


class TestTasaConversionOrgano:
    def test_empty(self):
        out = tasa_conversion_organo(_empty_df())
        assert out.empty

    def test_min_5_lics_filter(self):
        df = pd.DataFrame(
            {
                "id_externo": [f"id-{i}" for i in range(10)],
                "organo_contratacion": ["OrgA"] * 6 + ["OrgB"] * 4,
                "estado": ["ADJ"] * 3 + ["PUB"] * 3 + ["ADJ"] * 4,
            }
        )
        out = tasa_conversion_organo(df)
        # OrgB solo tiene 4 lics → filtrado
        assert "OrgA" in out["organo"].values
        assert "OrgB" not in out["organo"].values
        orga_row = out[out["organo"] == "OrgA"].iloc[0]
        assert orga_row["tasa"] == pytest.approx(50.0)


# ─── calidad_dato ───────────────────────────────────────────────────────────


class TestCalidadDato:
    def test_empty_returns_zeros(self):
        out = calidad_dato(_empty_df())
        assert out["pct_cpv_valido"] == 0.0
        assert out["pct_importe"] == 0.0

    def test_completitud(self):
        df = pd.DataFrame(
            {
                "id_externo": ["a", "b", "c", "d"],
                "cpv": ["72000000", "72000000", "ABC", None],  # 2 de 4 válidos
                "importe": [100, 200, None, 400],  # 3 de 4
                "fecha_publicacion": pd.to_datetime(
                    ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"], utc=True
                ),
                "titulo": ["Título largo", "OK buen título", "x", None],  # 2 de 4 válidos
            }
        )
        out = calidad_dato(df)
        assert out["pct_cpv_valido"] == 50.0
        assert out["pct_importe"] == 75.0
        assert out["pct_fecha_pub"] == 100.0
        assert out["pct_titulo"] == 50.0


class TestScoreOportunidad:
    """Tests para score_oportunidad — suma ponderada 0-100."""

    def _df_scoring(self) -> pd.DataFrame:
        now = pd.Timestamp.utcnow()
        return pd.DataFrame(
            {
                "id_externo": ["lic-1", "lic-2", "lic-3"],
                "titulo": [
                    "Implementación S/4HANA para ERP corporativo",
                    "Mantenimiento FI/CO sistema existente",
                    "Adquisición de material de oficina",
                ],
                "descripcion": [
                    "migración e integración completa",
                    "soporte anual a módulos financieros",
                    "folios, bolígrafos y grapadoras",
                ],
                "importe": [2_000_000.0, 500_000.0, 10_000.0],
                "fecha_fin_plazo": [
                    now + pd.Timedelta(days=30),
                    now + pd.Timedelta(days=15),
                    now - pd.Timedelta(days=5),  # vencida
                ],
                "cpv": ["72200000", "72200000", "30100000"],
                "modulos": [["FI", "CO", "MM", "SD"], ["FI", "CO"], []],
                "modulos_str": ["FI, CO, MM, SD", "FI, CO", ""],
            }
        )

    def test_empty_df(self):
        out = score_oportunidad(pd.DataFrame())
        assert out.empty
        assert set(out.columns) == {"id_externo", "score", "banda", "desglose"}

    def test_returns_expected_columns(self):
        df = self._df_scoring()
        out = score_oportunidad(df)
        assert list(out.columns) == ["id_externo", "score", "banda", "desglose"]
        assert len(out) == 3
        assert out["score"].dtype.kind in "iu"

    def test_scores_in_range_0_100(self):
        df = self._df_scoring()
        out = score_oportunidad(df)
        assert (out["score"] >= 0).all()
        assert (out["score"] <= 100).all()

    def test_sap_project_scores_higher_than_office_supplies(self):
        """Una licitación SAP grande debe puntuar más que material de oficina."""
        df = self._df_scoring()
        out = score_oportunidad(df).set_index("id_externo")
        assert out.loc["lic-1", "score"] > out.loc["lic-3", "score"]
        # lic-1 tiene S/4HANA + 4 módulos + importe alto → debe ser caliente/atractiva
        assert out.loc["lic-1", "score"] >= 50

    def test_desglose_sums_approximately_to_score(self):
        """Los valores del desglose deben sumar (±2 por redondeos) al score."""
        df = self._df_scoring()
        out = score_oportunidad(df)
        for _, row in out.iterrows():
            suma = sum(row["desglose"].values())
            assert abs(suma - row["score"]) <= 2, f"desglose {suma} vs score {row['score']}"

    def test_banda_assigned_from_score(self):
        df = self._df_scoring()
        out = score_oportunidad(df)
        for _, row in out.iterrows():
            s = row["score"]
            banda = row["banda"]
            if s >= 75:
                assert "Caliente" in banda
            elif s >= 50:
                assert "Atractiva" in banda
            elif s >= 25:
                assert "Tibia" in banda
            else:
                assert "Descarte" in banda

    def test_custom_weights_override(self):
        """Si se pasan pesos custom, deben aplicarse."""
        df = self._df_scoring()
        # Zero-out todo excepto importe → score proporcional sólo a importe
        custom = {
            "importe": 100.0,
            "plazo": 0.0,
            "modulos_sap": 0.0,
            "portfolio_match": 0.0,
            "s4hana_boost": 0.0,
            "competencia": 0.0,
            "riesgo": 0.0,
        }
        out = score_oportunidad(df, weights=custom).set_index("id_externo")
        # El importe más alto debe tener el score más alto
        assert out.loc["lic-1", "score"] >= out.loc["lic-2", "score"]
        assert out.loc["lic-2", "score"] >= out.loc["lic-3", "score"]

    def test_expired_plazo_gets_zero_plazo_points(self):
        """Una licitación con fecha_fin_plazo en el pasado no suma puntos en plazo."""
        df = self._df_scoring()
        out = score_oportunidad(df).set_index("id_externo")
        # lic-3 tiene plazo vencido → desglose["plazo"] == 0
        assert out.loc["lic-3", "desglose"]["plazo"] == 0

    def test_with_adjudicaciones_adds_competencia_signal(self):
        """Adjudicaciones históricas con baja mediana de ofertas suman en 'competencia'."""
        df = self._df_scoring()
        # adj.licitacion_id debe matchear df.id_externo para resolver cpv via merge
        adj = pd.DataFrame(
            {
                "licitacion_id": ["lic-1", "lic-2"],
                "n_ofertas_recibidas": [1, 2],  # mediana=1.5 < 3 → competencia baja en CPV 72
                "empresa_key": ["A", "B"],
                "nombre": ["Empresa A", "Empresa B"],
                "importe_adjudicado": [100000.0, 200000.0],
            }
        )
        out = score_oportunidad(df, adj).set_index("id_externo")
        # lic-1 y lic-2 (CPV 72) ganan punto por baja competencia
        assert out.loc["lic-1", "desglose"]["competencia"] > 0
        # lic-3 (CPV 30) no está en el mapa de CPVs con histórico → 0
        assert out.loc["lic-3", "desglose"]["competencia"] == 0
