"""Pipeline completo: descarga -> parseo -> filtrado SAP -> persistencia."""

from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta

from db.database import (
    init_db,
    log_extraccion,
    replace_adjudicaciones,
    upsert_licitaciones,
)
from db.dlq import record_failure
from observability import (
    AlertLevel,
    bind_run_context,
    get_logger,
    notify,
    record_run,
)
from scraper.bulk_downloader import (
    CircuitOpenError,
    download_month,
    iter_xml_files,
)
from scraper.codice_parser import parse_atom_bytes

log = get_logger(__name__)


def process_month(year: int, month: int, *, run_id: str | None = None, force: bool = False) -> dict:
    """Procesa un mes: descarga ZIP, parsea, filtra SAP, persiste."""
    fuente = f"bulk_{year}{month:02d}"
    try:
        zip_path = download_month(year, month, force=force)
    except CircuitOpenError as e:
        log.error("month_circuit_open", year=year, month=month, error=str(e))
        record_failure(run_id, fuente, e, scope="download")
        notify(
            AlertLevel.ERROR,
            "PLACSP circuit breaker abierto",
            "El scraper no pudo descargar por fallos consecutivos en PLACSP.",
            year=year,
            month=month,
        )
        return {"year": year, "month": month, "status": "circuit_open"}
    except Exception as e:
        log.exception("month_download_error", year=year, month=month)
        record_failure(run_id, fuente, e, scope="download")
        return {"year": year, "month": month, "status": "error_descarga"}

    if zip_path is None:
        return {"year": year, "month": month, "status": "no_publicado"}

    sap_encontradas = []
    adj_por_lic: dict[str, list] = {}
    entries_error = 0
    for filename, content in iter_xml_files(zip_path):
        log.info("xml_parse_start", filename=filename)
        try:
            for lic, adjudicaciones in parse_atom_bytes(content):
                sap_encontradas.append(lic)
                if adjudicaciones:
                    adj_por_lic[lic.id_externo] = adjudicaciones
        except Exception as e:
            log.exception("xml_parse_error", filename=filename, year=year, month=month)
            record_failure(run_id, fuente, e, scope="parse", payload_ref=filename)
            entries_error += 1

    try:
        nuevas, actualizadas = upsert_licitaciones(sap_encontradas)
    except Exception as e:
        log.exception("month_persist_error", year=year, month=month)
        record_failure(run_id, fuente, e, scope="persist_licitaciones")
        return {"year": year, "month": month, "status": "error_persistencia"}

    n_adj = 0
    for lic_id, adjs in adj_por_lic.items():
        try:
            n_adj += replace_adjudicaciones(lic_id, adjs)
        except Exception as e:
            log.exception("adj_persist_error", licitacion_id=lic_id)
            record_failure(run_id, fuente, e, scope="persist_adjudicaciones", payload_ref=lic_id)

    log_extraccion(
        fuente=fuente,
        nuevas=nuevas,
        actualizadas=actualizadas,
        total=len(sap_encontradas),
        notas=f"SAP:{len(sap_encontradas)} adj:{n_adj} errors:{entries_error}",
    )
    return {
        "year": year,
        "month": month,
        "status": "ok",
        "sap_matches": len(sap_encontradas),
        "adjudicaciones": n_adj,
        "nuevas": nuevas,
        "actualizadas": actualizadas,
        "entries_error": entries_error,
    }


def _summarize(results: list[dict], metrics) -> None:
    for r in results:
        metrics.months_attempted += 1
        if r["status"] == "ok":
            metrics.months_ok += 1
            metrics.licitaciones_nuevas += r.get("nuevas", 0)
            metrics.licitaciones_actualizadas += r.get("actualizadas", 0)
            metrics.adjudicaciones += r.get("adjudicaciones", 0)
            metrics.errores_parseo += r.get("entries_error", 0)
        elif r["status"] == "no_publicado":
            metrics.months_ok += 1
        else:
            metrics.months_failed += 1
            if r["status"] == "error_descarga":
                metrics.errores_descarga += 1


def update_recent(months_back: int = 3) -> list[dict]:
    """Actualiza los últimos N meses (idempotente gracias al upsert)."""
    init_db()
    today = date.today()
    run_id = bind_run_context(entrypoint="update_recent", months_back=months_back)
    with record_run(run_id) as metrics:
        results = []
        for i in range(months_back):
            target = today - relativedelta(months=i)
            results.append(process_month(target.year, target.month, run_id=run_id))
        _summarize(results, metrics)
    return results


def backfill(start_year: int, start_month: int) -> list[dict]:
    """Backfill desde una fecha histórica hasta hoy."""
    init_db()
    today = date.today()
    cur = date(start_year, start_month, 1)
    run_id = bind_run_context(entrypoint="backfill", start_year=start_year, start_month=start_month)
    with record_run(run_id) as metrics:
        results = []
        while cur <= today:
            results.append(process_month(cur.year, cur.month, run_id=run_id))
            cur += relativedelta(months=1)
        _summarize(results, metrics)
    return results
