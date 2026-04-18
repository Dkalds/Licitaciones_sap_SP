"""Tests para scraper/filters.py — detección de keywords SAP."""
from __future__ import annotations

from scraper.filters import matches_sap


class TestMatchesSap:
    # ── Casos positivos básicos ──────────────────────────────────────────
    def test_keyword_sap_basico(self):
        found, kws = matches_sap("Contrato de mantenimiento SAP")
        assert found is True
        # El regex puede capturar la keyword con contexto (ej. "mantenimiento sap")
        # si la keyword en config incluye esa frase; lo importante es que found=True
        assert any("sap" in k for k in kws)

    def test_keyword_s4hana(self):
        found, _kws = matches_sap("Migración a S/4HANA en el Ministerio")
        assert found is True

    def test_keyword_abap(self):
        found, kws = matches_sap("Desarrollo ABAP para módulo FI")
        assert found is True
        assert "abap" in kws

    def test_keyword_fiori(self):
        found, _kws = matches_sap("Implantación Fiori en ayuntamiento")
        assert found is True

    def test_keyword_en_summary(self):
        found, _kws = matches_sap(None, "Proyecto SAP S/4HANA completo")
        assert found is True

    def test_multiples_keywords_devuelve_todas(self):
        found, kws = matches_sap("Soporte SAP ABAP y Fiori")
        assert found is True
        assert any("sap" in k for k in kws)
        assert any("abap" in k for k in kws)
        assert any("fiori" in k for k in kws)

    def test_case_insensitive(self):
        found, _kws = matches_sap("sistema sap hana")
        assert found is True

    # ── Falsos positivos — palabras que contienen 'sap' pero no son SAP ──
    def test_no_falso_positivo_desaparecer(self):
        found, _ = matches_sap("El proyecto desapareció del portal")
        assert found is False

    def test_no_falso_positivo_saping(self):
        found, _ = matches_sap("saping is not a SAP product")
        # "saping" no debería coincidir con word boundary, pero "SAP" sí
        assert found is True  # "SAP" sí coincide

    def test_no_match_texto_irrelevante(self):
        found, kws = matches_sap("Mantenimiento de instalaciones eléctricas")
        assert found is False
        assert kws == []

    # ── Entradas vacías / None ───────────────────────────────────────────
    def test_none_devuelve_false(self):
        found, kws = matches_sap(None)
        assert found is False
        assert kws == []

    def test_string_vacio_devuelve_false(self):
        found, _kws = matches_sap("")
        assert found is False

    def test_multiples_none(self):
        found, _kws = matches_sap(None, None, None)
        assert found is False

    def test_primero_none_segundo_con_keyword(self):
        found, _kws = matches_sap(None, "SAP ERP implantación")
        assert found is True

    # ── Retorno: lista ordenada de keywords ─────────────────────────────
    def test_keywords_devueltas_en_minusculas(self):
        _, kws = matches_sap("SAP ABAP")
        assert all(k == k.lower() for k in kws)

    def test_keywords_devueltas_sin_duplicados(self):
        _, kws = matches_sap("SAP sap SAP")
        assert kws.count("sap") == 1
