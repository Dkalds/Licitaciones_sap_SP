"""Tests para dashboard/normalize.py — normalización de empresas y NIFs."""
from __future__ import annotations

import pytest
from dashboard.normalize import normalize_company, normalize_nif


class TestNormalizeCompany:
    # ── Eliminación de sufijos societarios ──────────────────────────────
    def test_elimina_sa(self):
        assert normalize_company("Empresa Ejemplo, S.A.") == "EMPRESA EJEMPLO"

    def test_elimina_sl(self):
        assert normalize_company("Tech Solutions S.L.") == "TECH SOLUTIONS"

    def test_elimina_sau(self):
        assert normalize_company("Holding Group, S.A.U.") == "HOLDING GROUP"

    def test_elimina_slu(self):
        assert normalize_company("Digital S.L.U.") == "DIGITAL"

    def test_elimina_sociedad_anonima(self):
        result = normalize_company("Constructora SOCIEDAD ANÓNIMA")
        assert "SOCIEDAD" not in result
        assert "ANONIMA" not in result

    def test_elimina_gmbh(self):
        assert normalize_company("SAP Deutschland GmbH") == "SAP DEUTSCHLAND"

    def test_elimina_ltd(self):
        assert normalize_company("Oracle Ltd") == "ORACLE"

    # ── Normalización de tildes y mayúsculas ─────────────────────────────
    def test_mayusculas(self):
        result = normalize_company("empresa ejemplo")
        assert result == result.upper()

    def test_sin_tildes(self):
        result = normalize_company("Información y Tecnología")
        assert "Á" not in result
        assert "ó" not in result

    # ── Deduplicación: misma empresa, variantes distintas ───────────────
    def test_misma_empresa_variantes(self):
        assert normalize_company("IBM España, S.A.") == normalize_company("IBM ESPAÑA SA")

    def test_misma_empresa_con_y_sin_puntos(self):
        assert normalize_company("Accenture S.L.") == normalize_company("Accenture SL")

    # ── Entradas inválidas ───────────────────────────────────────────────
    def test_none_devuelve_none(self):
        assert normalize_company(None) is None

    def test_string_vacio_devuelve_none(self):
        assert normalize_company("") is None

    def test_solo_sufijo_devuelve_none(self):
        # Una empresa que es solo "S.A." debería resultar en None o vacío
        result = normalize_company("S.A.")
        assert result is None or result == ""

    def test_no_string_devuelve_none(self):
        assert normalize_company(123) is None  # type: ignore[arg-type]


class TestNormalizeNif:
    # ── Normalización básica ─────────────────────────────────────────────
    def test_elimina_espacios(self):
        assert normalize_nif("A 12345678") == "A12345678"

    def test_elimina_guiones(self):
        assert normalize_nif("A-12345678") == "A12345678"

    def test_elimina_puntos(self):
        assert normalize_nif("A.12345678") == "A12345678"

    def test_mayusculas(self):
        assert normalize_nif("a12345678") == "A12345678"

    def test_combina_transformaciones(self):
        assert normalize_nif(" a-123.456-78 ") == "A12345678"

    # ── Consistencia: mismos NIF, distintos formatos ─────────────────────
    def test_mismo_nif_formatos_distintos(self):
        assert normalize_nif("B-12345678") == normalize_nif("B 12345678")

    # ── Entradas inválidas ───────────────────────────────────────────────
    def test_none_devuelve_none(self):
        assert normalize_nif(None) is None

    def test_vacio_devuelve_none(self):
        assert normalize_nif("") is None

    def test_solo_separadores_devuelve_none(self):
        assert normalize_nif("- . -") is None
