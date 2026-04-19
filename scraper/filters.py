"""Filtros para detectar licitaciones relacionadas con SAP."""

from __future__ import annotations

import re

from config import SAP_KEYWORDS

# Compilamos un regex con word boundaries para evitar falsos positivos
# (ej: 'sap' dentro de otra palabra como 'desaparecer')
_SAP_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in SAP_KEYWORDS) + r")\b",
    flags=re.IGNORECASE,
)


def matches_sap(*texts: str | None) -> tuple[bool, list[str]]:
    """Comprueba si alguno de los textos contiene keywords SAP.

    Returns:
        (coincide, lista_de_keywords_encontradas)
    """
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        for match in _SAP_PATTERN.findall(text):
            found.add(match.lower())
    return bool(found), sorted(found)
