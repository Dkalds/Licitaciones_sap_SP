"""API REST mínima sobre la BD de licitaciones.

Arranca con::

    uvicorn api.main:app --host 0.0.0.0 --port 8000

Autenticación vía header ``X-API-Key`` (opcional). Si ``API_KEY`` no está
definida, la API funciona en modo abierto y conviene protegerla detrás de un
reverse proxy.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import API_KEY, API_RATE_LIMIT
from db.database import connect, count_licitaciones, fts_available, init_db, search_fts
from observability import configure_logging, get_logger
from scheduler.healthcheck import run_check

configure_logging()
log = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Licitaciones SAP API",
    description="Acceso de solo lectura a licitaciones SAP extraídas de PLACSP.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    log.info("api_startup")
    if not API_KEY.strip():
        log.warning("api_key_not_configured_api_is_open")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = API_KEY.strip()
    if not expected:
        return
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, Any]:
    return run_check()


@app.get("/v1/licitaciones", dependencies=[Depends(require_api_key)], tags=["licitaciones"])
@limiter.limit(API_RATE_LIMIT)
def list_licitaciones(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    cpv_prefix: str | None = Query(None, max_length=8, pattern=r"^[0-9]{2,8}$"),
    ccaa: str | None = Query(None, max_length=80),
    min_importe: float | None = Query(None, ge=0),
    q: str | None = Query(None, max_length=120),
) -> dict[str, Any]:
    # FTS fast path: use FTS5 when only 'q' is provided and FTS is available
    use_fts = q and not cpv_prefix and not ccaa and min_importe is None and fts_available()
    if use_fts:
        assert q is not None  # for type narrowing
        rows, total = search_fts(q, limit=limit, offset=offset)
        return {
            "count": len(rows),
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": rows,
        }

    where: list[str] = []
    where_params: list[Any] = []
    if cpv_prefix:
        where.append("cpv LIKE ?")
        where_params.append(f"{cpv_prefix}%")
    if ccaa:
        where.append("ccaa = ?")
        where_params.append(ccaa)
    if min_importe is not None:
        where.append("importe >= ?")
        where_params.append(min_importe)
    if q:
        q_safe = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(titulo LIKE ? ESCAPE '\\' OR descripcion LIKE ? ESCAPE '\\')")
        where_params.extend([f"%{q_safe}%", f"%{q_safe}%"])
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = "SELECT * FROM licitaciones" + where_sql + " ORDER BY fecha_publicacion DESC LIMIT ? OFFSET ?"
    count_sql = "SELECT COUNT(*) FROM licitaciones" + where_sql

    with connect() as c:
        filtered_total = c.execute(count_sql, where_params).fetchone()[0]
        cur = c.execute(sql, where_params + [limit, offset])
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]

    return {
        "count": len(rows),
        "total": int(filtered_total),
        "limit": limit,
        "offset": offset,
        "items": rows,
    }


@app.get("/v1/runs", dependencies=[Depends(require_api_key)], tags=["meta"])
@limiter.limit(API_RATE_LIMIT)
def list_runs(request: Request, limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
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
