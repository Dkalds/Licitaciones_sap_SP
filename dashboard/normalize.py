"""Normalización de nombres de empresas para deduplicar adjudicatarios."""
from __future__ import annotations

import re
import unicodedata

# Sufijos societarios (España + frecuentes UE) — se eliminan al final
_LEGAL_SUFFIXES = [
    r"S\.?\s?A\.?\s?U\.?",
    r"S\.?\s?L\.?\s?U\.?",
    r"S\.?\s?A\.?\s?S\.?",
    r"S\.?\s?L\.?\s?P\.?",
    r"S\.?\s?L\.?\s?N\.?\s?E\.?",
    r"S\.?\s?C\.?\s?P\.?",
    r"S\.?\s?A\.?",
    r"S\.?\s?L\.?",
    r"S\.?\s?C\.?",
    r"S\.?\s?COOP\.?",
    r"SOCIEDAD\s+AN[OÓ]NIMA(\s+UNIPERSONAL)?",
    r"SOCIEDAD\s+LIMITADA(\s+UNIPERSONAL)?",
    r"SOCIEDAD\s+COOPERATIVA",
    r"COMPA[ÑN][ÍI]A",
    r"\bGMBH\b",
    r"\bLTD\b",
    r"\bLLC\b",
    r"\bINC\b",
    r"\bAG\b",
    r"\bBV\b",
    r"\bN\.?V\.?",
    r"\bU\.?T\.?E\.?",  # UTE: las marcamos aparte
]

_SUFFIX_RE = re.compile(
    r"(?:^|[\s,\.\-])(" + "|".join(_LEGAL_SUFFIXES) + r")\s*$",
    flags=re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_company(name: str | None) -> str | None:
    """Normaliza un nombre de empresa para agrupar duplicados.

    Pasos: mayúsculas → sin tildes → strip puntuación → quita sufijos
    societarios (S.A., S.L., GmbH...) → colapsa espacios.
    """
    if not name or not isinstance(name, str):
        return None
    s = name.strip().upper()
    s = _strip_accents(s)
    # Quitar sufijos societarios (varias pasadas por si hay encadenados)
    for _ in range(3):
        new = _SUFFIX_RE.sub("", s).strip(" ,.-")
        if new == s:
            break
        s = new
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s or None


def normalize_nif(nif: str | None) -> str | None:
    """Normaliza un NIF/CIF: quita espacios, guiones, mayúsculas."""
    if not nif or not isinstance(nif, str):
        return None
    s = re.sub(r"[\s\-\.]", "", nif).upper()
    return s or None
