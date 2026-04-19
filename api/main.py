"""API REST mínima sobre la BD de licitaciones.

Arranca con::

    uvicorn api.main:app --host 0.0.0.0 --port 8000

Autenticación vía header ``X-API-Key`` (opcional). Si ``API_KEY`` no está
definida, la API funciona en modo abierto y conviene protegerla detrás de un
reverse proxy.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from db.database import connect, count_licitaciones, init_db
from observability import configure_logging, get_logger
from scheduler.healthcheck import run_check

configure_logging()
log = get_logger(__name__)

app = FastAPI(
    title="Licitaciones SAP API",
    description="Acceso de solo lectura a licitaciones SAP extraídas de PLACSP.",
    version="1.0.0",
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    log.info("api_startup")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("API_KEY", "").strip()
    if not expected:
        return
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, Any]:
    return run_check()


@app.get("/v1/licitaciones", dependencies=[Depends(require_api_key)], tags=["licitaciones"])
def list_licitaciones(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    cpv_prefix: str | None = Query(None, max_length=8, pattern=r"^[0-9]{2,8}$"),
    ccaa: str | None = Query(None, max_length=80),
    min_importe: float | None = Query(None, ge=0),
    q: str | None = Query(None, max_length=120),
) -> dict[str, Any]:
    where: list[str] = []
    params: list[Any] = []
    if cpv_prefix:
        where.append("cpv LIKE ?")
        params.append(f"{cpv_prefix}%")
    if ccaa:
        where.append("ccaa = ?")
        params.append(ccaa)
    if min_importe is not None:
        where.append("importe >= ?")
        params.append(min_importe)
    if q:
        where.append("(titulo LIKE ? OR descripcion LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    sql = "SELECT * FROM licitaciones"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha_publicacion DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with connect() as c:
        cur = c.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]

    return {
        "count": len(rows),
        "total": count_licitaciones(),
        "limit": limit,
        "offset": offset,
        "items": rows,
    }


@app.get("/v1/runs", dependencies=[Depends(require_api_key)], tags=["meta"])
def list_runs(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    with connect() as c:
        cur = c.execute(
            "SELECT run_id, started_at, ended_at, status, "
            "licitaciones_nuevas, licitaciones_actualizadas, "
            "months_ok, months_failed "
            "FROM extraction_runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]
    return {"count": len(rows), "items": rows}
