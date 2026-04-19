"""Tests para dashboard/utils/format.py y dashboard/utils/export.py."""

from __future__ import annotations

import pandas as pd

from dashboard.utils.format import fmt_eur

# ─── fmt_eur ─────────────────────────────────────────────────────────────────


class TestFmtEur:
    def test_none_returns_dash(self):
        assert fmt_eur(None) == "—"

    def test_nan_returns_dash(self):
        assert fmt_eur(float("nan")) == "—"

    def test_small_amount(self):
        assert fmt_eur(500.0) == "500 €"

    def test_thousands(self):
        result = fmt_eur(5_000.0)
        assert "k€" in result
        assert "5.0" in result

    def test_millions(self):
        result = fmt_eur(3_500_000.0)
        assert "M€" in result
        assert "3.50" in result

    def test_billions(self):
        result = fmt_eur(2_000_000_000.0)
        assert "B€" in result
        assert "2.00" in result

    def test_zero(self):
        assert fmt_eur(0.0) == "0 €"

    def test_negative_small(self):
        result = fmt_eur(-500.0)
        assert "€" in result

    def test_negative_millions(self):
        result = fmt_eur(-2_000_000.0)
        assert "M€" in result

    def test_exactly_1000(self):
        result = fmt_eur(1_000.0)
        assert "k€" in result

    def test_exactly_1_million(self):
        result = fmt_eur(1_000_000.0)
        assert "M€" in result

    def test_exactly_1_billion(self):
        result = fmt_eur(1_000_000_000.0)
        assert "B€" in result


# ─── to_excel_bytes ──────────────────────────────────────────────────────────


class TestToExcelBytes:
    def test_returns_non_empty_bytes(self):
        from dashboard.utils.export import to_excel_bytes

        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        data = to_excel_bytes(df)
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_excludes_modulos_column(self):
        from dashboard.utils.export import to_excel_bytes

        df = pd.DataFrame(
            {
                "titulo": ["Test"],
                "importe": [1000.0],
                "modulos": [["SAP", "HANA"]],
            }
        )
        data = to_excel_bytes(df)
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_handles_tz_aware_datetime(self):
        from dashboard.utils.export import to_excel_bytes

        df = pd.DataFrame(
            {
                "titulo": ["Test"],
                "fecha": pd.to_datetime(["2024-01-01"], utc=True),
            }
        )
        data = to_excel_bytes(df)
        assert isinstance(data, bytes)
