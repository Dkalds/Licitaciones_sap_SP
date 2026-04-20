"""Tests para dashboard/stats.py — funciones de estadísticas puras."""

from __future__ import annotations

import pandas as pd
import pytest

from dashboard.stats import (
    ccaa_mas_activa,
    concentracion_geografica,
    funnel_estados,
    hhi_concentracion,
    indice_novedad,
    kpis,
    lead_time_medio,
    media_movil,
    mes_pico,
    pct_oferta_unica,
    por_cpv,
    por_estado,
    por_mes,
    ratio_relicitacion,
    risk_flags,
    tasa_anulacion,
    top_organos,
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
