"""Pipeline completo: descarga -> parseo -> filtrado SAP -> persistencia."""
from __future__ import annotations

import logging
from datetime import date
from dateutil.relativedelta import relativedelta

from db.database import (init_db, log_extraccion,
                          replace_adjudicaciones, upsert_licitaciones)
from scraper.bulk_downloader import download_month, iter_xml_files
from scraper.codice_parser import parse_atom_bytes

log = logging.getLogger(__name__)


def process_month(year: int, month: int, force: bool = False) -> dict:
    """Procesa un mes: descarga ZIP, parsea, filtra SAP, persiste."""
    try:
        zip_path = download_month(year, month, force=force)
    except Exception:
        log.exception("Error descargando %d-%02d", year, month)
        return {"year": year, "month": month, "status": "error_descarga"}

    if zip_path is None:
        return {"year": year, "month": month, "status": "no_publicado"}

    sap_encontradas = []
    adj_por_lic: dict[str, list] = {}
    entries_error = 0
    for filename, content in iter_xml_files(zip_path):
        log.info("Parseando %s", filename)
        try:
            for lic, adjudicaciones in parse_atom_bytes(content):
                sap_encontradas.append(lic)
                if adjudicaciones:
                    adj_por_lic[lic.id_externo] = adjudicaciones
        except Exception:
            log.exception("Error parseando fichero %s del ZIP %d-%02d",
                          filename, year, month)
            entries_error += 1

    try:
        nuevas, actualizadas = upsert_licitaciones(sap_encontradas)
    except Exception:
        log.exception("Error persistiendo licitaciones de %d-%02d", year, month)
        return {"year": year, "month": month, "status": "error_persistencia"}

    n_adj = 0
    for lic_id, adjs in adj_por_lic.items():
        try:
            n_adj += replace_adjudicaciones(lic_id, adjs)
        except Exception:
            log.exception("Error persistiendo adjudicaciones de %s", lic_id)

    log_extraccion(
        fuente=f"bulk_{year}{month:02d}",
        nuevas=nuevas,
        actualizadas=actualizadas,
        total=len(sap_encontradas),
        notas=f"SAP:{len(sap_encontradas)} adj:{n_adj} errors:{entries_error}",
    )
    return {
        "year": year, "month": month, "status": "ok",
        "sap_matches": len(sap_encontradas),
        "adjudicaciones": n_adj,
        "nuevas": nuevas, "actualizadas": actualizadas,
        "entries_error": entries_error,
    }


def update_recent(months_back: int = 3) -> list[dict]:
    """Actualiza los últimos N meses (idempotente gracias al upsert)."""
    init_db()
    today = date.today()
    results = []
    for i in range(months_back):
        target = today - relativedelta(months=i)
        results.append(process_month(target.year, target.month))
    return results


def backfill(start_year: int, start_month: int) -> list[dict]:
    """Backfill desde una fecha histórica hasta hoy."""
    init_db()
    today = date.today()
    cur = date(start_year, start_month, 1)
    results = []
    while cur <= today:
        results.append(process_month(cur.year, cur.month))
        cur += relativedelta(months=1)
    return results
