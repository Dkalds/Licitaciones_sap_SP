"""Punto de entrada para ejecuciones programadas (cron / Task Scheduler).

Uso:
  python -m scheduler.run_update                # actualiza últimos 3 meses
  python -m scheduler.run_update --backfill 2024 1   # desde ene-2024
  python -m scheduler.run_update --months 6     # últimos 6 meses
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import count_licitaciones
from observability import (
    AlertLevel,
    configure_logging,
    get_logger,
    notify,
)
from scraper.pipeline import backfill, update_recent


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--months", type=int, default=3, help="Cuántos meses recientes refrescar (default 3)"
    )
    p.add_argument(
        "--backfill",
        nargs=2,
        type=int,
        metavar=("YEAR", "MONTH"),
        help="Backfill desde año/mes hasta hoy",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument(
        "--log-format",
        choices=("json", "console"),
        default=None,
        help="Formato de logs (default: auto)",
    )
    args = p.parse_args()

    configure_logging(
        level="DEBUG" if args.verbose else "INFO",
        json_logs=(args.log_format == "json") if args.log_format else None,
    )
    log = get_logger("run_update")

    try:
        if args.backfill:
            results = backfill(args.backfill[0], args.backfill[1])
        else:
            results = update_recent(args.months)
    except Exception as e:
        log.exception("pipeline_fatal_error")
        notify(AlertLevel.CRITICAL, "Pipeline licitaciones falló con error fatal", body=str(e))
        return 1

    failed = [r for r in results if r.get("status") not in ("ok", "no_publicado")]
    total_nuevas = sum(r.get("nuevas", 0) for r in results)
    total_act = sum(r.get("actualizadas", 0) for r in results)
    total_db = count_licitaciones()
    log.info(
        "pipeline_summary",
        nuevas=total_nuevas,
        actualizadas=total_act,
        total_bd=total_db,
        meses_fallidos=len(failed),
    )

    if failed:
        notify(
            AlertLevel.WARN,
            "Pipeline licitaciones con meses fallidos",
            body=f"{len(failed)} mes(es) con error.",
            meses_fallidos=[f"{r['year']}-{r['month']:02d}:{r['status']}" for r in failed],
            nuevas=total_nuevas,
            total_bd=total_db,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
