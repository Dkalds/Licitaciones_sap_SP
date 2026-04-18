"""Punto de entrada para ejecuciones programadas (cron / Task Scheduler).

Uso:
  python -m scheduler.run_update                # actualiza últimos 3 meses
  python -m scheduler.run_update --backfill 2024 1   # desde ene-2024
  python -m scheduler.run_update --months 6     # últimos 6 meses
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.pipeline import backfill, update_recent
from db.database import count_licitaciones


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--months", type=int, default=3,
                   help="Cuántos meses recientes refrescar (default 3)")
    p.add_argument("--backfill", nargs=2, type=int, metavar=("YEAR", "MONTH"),
                   help="Backfill desde año/mes hasta hoy")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("run_update")

    if args.backfill:
        results = backfill(args.backfill[0], args.backfill[1])
    else:
        results = update_recent(args.months)

    total_nuevas = sum(r.get("nuevas", 0) for r in results)
    total_act = sum(r.get("actualizadas", 0) for r in results)
    log.info("Resumen: %d nuevas, %d actualizadas. Total en BD: %d",
             total_nuevas, total_act, count_licitaciones())
    return 0


if __name__ == "__main__":
    sys.exit(main())
