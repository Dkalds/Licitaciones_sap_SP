"""Comprueba la watchlist tras cada ejecución del pipeline y envía alertas por email.

Lógica:
- Para cada entrada de la watchlist del usuario se consultan las licitaciones con
  ``fecha_publicacion >= last_notified_at`` (o últimos 30 días si es la primera vez).
- Si hay coincidencias se envía un único email resumen con todas ellas.
- Siempre se actualiza ``last_notified_at`` al terminar, para que la próxima
  ejecución solo vea licitaciones publicadas después de este momento.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from typing import Any

from db.database import connect
from db.watchlist import list_entries, matches_licitacion, update_last_notified
from observability import AlertLevel, get_logger, notify

log = get_logger(__name__)

# Ventana de búsqueda inicial cuando no hay last_notified_at previo
_LOOKBACK_DAYS = 30


def _user_key() -> str:
    """Misma derivación que usa el dashboard (hash del DASHBOARD_PASSWORD)."""
    seed = (
        os.environ.get("DASHBOARD_PASSWORD", "")
        or os.environ.get("COMPUTERNAME", "default")
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _query_licitaciones_since(cpv_prefix: str, since_date: str) -> list[dict[str, Any]]:
    """Devuelve licitaciones con fecha_publicacion >= since_date y CPV que empiece
    por cpv_prefix. El filtrado fino (keyword, importe, ccaa) lo hace
    matches_licitacion() en Python."""
    pattern = cpv_prefix + "%"
    with connect() as c:
        cur = c.execute(
            "SELECT id_externo, titulo, descripcion, organo_contratacion, "
            "cpv, importe, ccaa, estado, fecha_publicacion, url "
            "FROM licitaciones "
            "WHERE fecha_publicacion >= ? AND cpv LIKE ? "
            "ORDER BY fecha_publicacion DESC",
            (since_date, pattern),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


def _build_body(matches_by_entry: list[tuple[dict[str, Any], list[dict[str, Any]]]]) -> str:
    total = sum(len(lics) for _, lics in matches_by_entry)
    lines: list[str] = [
        f"Se han encontrado {total} licitación(es) que encajan con tu watchlist:\n"
    ]
    for entry, lics in matches_by_entry:
        parts = [f"CPV: {entry['cpv_prefix']}"]
        if entry.get("keyword"):
            parts.append(f"keyword: {entry['keyword']}")
        if entry.get("min_importe"):
            parts.append(f"importe ≥ {entry['min_importe']:,.0f} €")
        if entry.get("ccaa"):
            parts.append(f"CCAA: {entry['ccaa']}")
        lines.append(f"\n── {' | '.join(parts)} ──────────────────")
        for lic in lics[:10]:
            importe_str = f"{lic['importe']:,.0f} €" if lic.get("importe") else "—"
            url = lic.get("url") or ""
            lines.append(
                f"  • [{lic.get('fecha_publicacion', '?')}] {lic['titulo']}\n"
                f"    {lic.get('organo_contratacion') or '—'} | {importe_str}\n"
                f"    {url}"
            )
        if len(lics) > 10:
            lines.append(f"  … y {len(lics) - 10} más.")
    return "\n".join(lines)


def check_and_notify() -> int:
    """Comprueba la watchlist del usuario y envía email si hay coincidencias nuevas.

    Returns:
        Número total de licitaciones notificadas (0 si ninguna).
    """
    user_key = _user_key()
    entries = list_entries(user_key)

    if not entries:
        log.debug("watchlist_empty", user_key=user_key)
        return 0

    now_ts = datetime.utcnow().isoformat()
    default_since = (
        datetime.utcnow() - timedelta(days=_LOOKBACK_DAYS)
    ).date().isoformat()

    matches_by_entry: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []

    for entry in entries:
        raw_since = entry.get("last_notified_at") or default_since
        since_date = str(raw_since)[:10]  # truncar a YYYY-MM-DD

        candidates = _query_licitaciones_since(entry["cpv_prefix"], since_date)
        matched = [lic for lic in candidates if matches_licitacion(entry, lic)]

        log.debug(
            "watchlist_entry_checked",
            cpv=entry["cpv_prefix"],
            keyword=entry.get("keyword"),
            since=since_date,
            candidates=len(candidates),
            matches=len(matched),
        )

        if matched:
            matches_by_entry.append((entry, matched))

    # Siempre actualizamos last_notified_at para no acumular ventana
    for entry in entries:
        update_last_notified(int(entry["id"]), now_ts)

    if not matches_by_entry:
        log.info("watchlist_no_new_matches", entries=len(entries))
        return 0

    total = sum(len(lics) for _, lics in matches_by_entry)
    body = _build_body(matches_by_entry)

    notify(
        AlertLevel.INFO,
        f"Watchlist: {total} licitación(es) nueva(s)",
        body,
        entradas_con_coincidencias=len(matches_by_entry),
        total_coincidencias=total,
    )
    log.info(
        "watchlist_alert_sent",
        total=total,
        entries_with_matches=len(matches_by_entry),
    )
    return total
