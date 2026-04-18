"""Tests para dashboard/forecast.py — cálculos de fecha y duración."""
from __future__ import annotations

import pandas as pd
import pytest

from dashboard.forecast import estimate_end_date, to_months


class TestToMonths:
    def test_anual_12_meses(self):
        assert to_months(1, "ANN") == pytest.approx(12.0)

    def test_2_anios(self):
        assert to_months(2, "ANN") == pytest.approx(24.0)

    def test_meses_directo(self):
        assert to_months(6, "MON") == pytest.approx(6.0)

    def test_dias_aproximacion(self):
        result = to_months(30, "DAY")
        assert result == pytest.approx(30 / 30.4375, rel=1e-4)

    def test_semanas(self):
        result = to_months(4, "WEK")
        assert result == pytest.approx(4 * 7 / 30.4375, rel=1e-4)

    def test_unidad_desconocida_devuelve_none(self):
        assert to_months(5, "XXX") is None

    def test_valor_none_devuelve_none(self):
        assert to_months(None, "ANN") is None

    def test_unidad_none_devuelve_none(self):
        assert to_months(12, None) is None

    def test_valor_nan_devuelve_none(self):
        assert to_months(float("nan"), "MON") is None

    def test_unidad_case_insensitive(self):
        assert to_months(1, "ann") == pytest.approx(12.0)


class TestEstimateEndDate:
    def _ts(self, date_str: str) -> pd.Timestamp:
        return pd.Timestamp(date_str)

    def test_fecha_fin_explicita_tiene_prioridad(self):
        start = self._ts("2024-01-01")
        explicit = self._ts("2025-06-30")
        result = estimate_end_date(start, 12.0, fecha_fin_explicit=explicit)
        assert result == explicit

    def test_calcula_desde_inicio_y_duracion(self):
        start = self._ts("2024-01-01")
        result = estimate_end_date(start, 12.0)
        assert result == self._ts("2025-01-01")

    def test_start_none_devuelve_none(self):
        assert estimate_end_date(None, 12.0) is None

    def test_duracion_none_devuelve_none(self):
        start = self._ts("2024-01-01")
        assert estimate_end_date(start, None) is None

    def test_duracion_cero_devuelve_none(self):
        start = self._ts("2024-01-01")
        assert estimate_end_date(start, 0.0) is None

    def test_duracion_negativa_devuelve_none(self):
        start = self._ts("2024-01-01")
        assert estimate_end_date(start, -6.0) is None

    def test_fecha_fin_nat_usa_calculo(self):
        start = self._ts("2024-01-01")
        result = estimate_end_date(start, 6.0, fecha_fin_explicit=pd.NaT)
        assert result is not None
        assert result == self._ts("2024-07-01")
