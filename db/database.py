"""Capa de persistencia SQLite / Turso (libSQL) para licitaciones."""
from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Iterable, Iterator

import libsql

from config import DB_PATH, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, TURSO_LOCAL_DB


SCHEMA = """
CREATE TABLE IF NOT EXISTS licitaciones (
    id_externo          TEXT PRIMARY KEY,
    titulo              TEXT NOT NULL,
    descripcion         TEXT,
    organo_contratacion TEXT,
    importe             REAL,
    moneda              TEXT DEFAULT 'EUR',
    cpv                 TEXT,
    tipo_contrato       TEXT,
    estado              TEXT,
    fecha_publicacion   TEXT,
    fecha_limite        TEXT,
    url                 TEXT,
    raw_keywords        TEXT,
    provincia           TEXT,
    ccaa                TEXT,
    nuts_code           TEXT,
    duracion_valor      REAL,
    duracion_unidad     TEXT,
    fecha_inicio        TEXT,
    fecha_fin           TEXT,
    prorroga_descripcion TEXT,
    fecha_extraccion    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fecha_pub ON licitaciones(fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_organo    ON licitaciones(organo_contratacion);
CREATE INDEX IF NOT EXISTS idx_estado    ON licitaciones(estado);
CREATE INDEX IF NOT EXISTS idx_cpv       ON licitaciones(cpv);
CREATE INDEX IF NOT EXISTS idx_ccaa      ON licitaciones(ccaa);

CREATE TABLE IF NOT EXISTS adjudicaciones (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    licitacion_id           TEXT NOT NULL,
    nif                     TEXT,
    nombre                  TEXT NOT NULL,
    provincia               TEXT,
    ccaa                    TEXT,
    nuts_code               TEXT,
    importe_adjudicado      REAL,
    importe_pagable         REAL,
    fecha_adjudicacion      TEXT,
    es_pyme                 INTEGER,
    n_ofertas_recibidas     INTEGER,
    oferta_minima           REAL,
    oferta_maxima           REAL,
    result_code             TEXT,
    result_description      TEXT,
    fecha_extraccion        TEXT NOT NULL,
    UNIQUE(licitacion_id, nif, importe_adjudicado),
    FOREIGN KEY(licitacion_id) REFERENCES licitaciones(id_externo)
);
CREATE INDEX IF NOT EXISTS idx_adj_lic    ON adjudicaciones(licitacion_id);
CREATE INDEX IF NOT EXISTS idx_adj_nif    ON adjudicaciones(nif);
CREATE INDEX IF NOT EXISTS idx_adj_ccaa   ON adjudicaciones(ccaa);

CREATE TABLE IF NOT EXISTS extracciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT NOT NULL,
    fuente          TEXT NOT NULL,
    nuevas          INTEGER DEFAULT 0,
    actualizadas    INTEGER DEFAULT 0,
    total_revisadas INTEGER DEFAULT 0,
    notas           TEXT
);
"""


@dataclass
class Adjudicacion:
    licitacion_id: str
    nombre: str
    nif: str | None = None
    provincia: str | None = None
    ccaa: str | None = None
    nuts_code: str | None = None
    importe_adjudicado: float | None = None
    importe_pagable: float | None = None
    fecha_adjudicacion: str | None = None
    es_pyme: int | None = None  # 0/1/None
    n_ofertas_recibidas: int | None = None
    oferta_minima: float | None = None
    oferta_maxima: float | None = None
    result_code: str | None = None
    result_description: str | None = None
    fecha_extraccion: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


@dataclass
class Licitacion:
    id_externo: str
    titulo: str
    descripcion: str | None = None
    organo_contratacion: str | None = None
    importe: float | None = None
    moneda: str = "EUR"
    cpv: str | None = None
    tipo_contrato: str | None = None
    estado: str | None = None
    fecha_publicacion: str | None = None
    fecha_limite: str | None = None
    url: str | None = None
    raw_keywords: str | None = None
    provincia: str | None = None
    ccaa: str | None = None
    nuts_code: str | None = None
    duracion_valor: float | None = None
    duracion_unidad: str | None = None  # ANN/MON/DAY
    fecha_inicio: str | None = None
    fecha_fin: str | None = None
    prorroga_descripcion: str | None = None
    fecha_extraccion: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


@contextmanager
def connect() -> Iterator:
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        conn = libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    else:
        conn = libsql.connect(str(DB_PATH))
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_NEW_COLUMNS_LICITACIONES = [
    ("duracion_valor", "REAL"),
    ("duracion_unidad", "TEXT"),
    ("fecha_inicio", "TEXT"),
    ("fecha_fin", "TEXT"),
    ("prorroga_descripcion", "TEXT"),
]


_VALID_COLUMN_NAME = re.compile(r"^[a-zA-Z_]\w*$")


def _migrate(conn) -> None:
    """Aplica ALTER TABLE ADD COLUMN para BDs preexistentes."""
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(licitaciones)").fetchall()}
    for name, ctype in _NEW_COLUMNS_LICITACIONES:
        if not _VALID_COLUMN_NAME.match(name):
            raise ValueError(f"Nombre de columna no válido: {name!r}")
        if name not in cols:
            conn.execute(
                f"ALTER TABLE licitaciones ADD COLUMN {name} {ctype}")


def init_db() -> None:
    with connect() as c:
        for stmt in SCHEMA.split(";"):
            stmt = stmt.strip()
            if stmt:
                c.execute(stmt)
        _migrate(c)


def upsert_licitaciones(items: Iterable[Licitacion]) -> tuple[int, int]:
    """Inserta o actualiza licitaciones. Devuelve (nuevas, actualizadas)."""
    nuevas = 0
    actualizadas = 0
    with connect() as c:
        for lic in items:
            existing = c.execute(
                "SELECT 1 FROM licitaciones WHERE id_externo = ?",
                [lic.id_externo],
            ).fetchone()
            data = asdict(lic)
            keys = list(data.keys())
            for k in keys:
                if not _VALID_COLUMN_NAME.match(k):
                    raise ValueError(f"Nombre de columna no válido: {k!r}")
            vals = list(data.values())
            cols = ", ".join(keys)
            placeholders = ", ".join("?" for _ in keys)
            updates = ", ".join(f"{k}=excluded.{k}" for k in keys if k != "id_externo")
            c.execute(
                f"INSERT INTO licitaciones ({cols}) VALUES ({placeholders}) "
                f"ON CONFLICT(id_externo) DO UPDATE SET {updates}",
                vals,
            )
            if existing:
                actualizadas += 1
            else:
                nuevas += 1
    return nuevas, actualizadas


def replace_adjudicaciones(licitacion_id: str,
                            items: Iterable[Adjudicacion]) -> int:
    """Reemplaza todas las adjudicaciones de una licitación (idempotente)."""
    items = list(items)
    with connect() as c:
        c.execute("DELETE FROM adjudicaciones WHERE licitacion_id = ?",
                  [licitacion_id])
        n = 0
        for adj in items:
            data = asdict(adj)
            keys = list(data.keys())
            for k in keys:
                if not _VALID_COLUMN_NAME.match(k):
                    raise ValueError(f"Nombre de columna no válido: {k!r}")
            vals = list(data.values())
            cols = ", ".join(keys)
            placeholders = ", ".join("?" for _ in keys)
            c.execute(
                f"INSERT OR IGNORE INTO adjudicaciones ({cols}) "
                f"VALUES ({placeholders})",
                vals,
            )
            n += 1
    return n


def log_extraccion(fuente: str, nuevas: int, actualizadas: int,
                   total: int, notas: str = "") -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO extracciones "
            "(fecha, fuente, nuevas, actualizadas, total_revisadas, notas) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), fuente, nuevas,
             actualizadas, total, notas),
        )


def count_licitaciones() -> int:
    with connect() as c:
        return c.execute("SELECT COUNT(*) FROM licitaciones").fetchone()[0]
