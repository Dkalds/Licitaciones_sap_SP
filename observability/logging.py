"""Logging estructurado con structlog + correlation IDs por run.

Uso típico::

    from observability import configure_logging, get_logger, bind_run_context

    configure_logging(json_logs=True)
    log = get_logger(__name__)
    bind_run_context(run_id="abc123", module="scraper")
    log.info("month_start", year=2026, month=4)

Cuando ``json_logs=False`` (interactivo), imprime en color para lectura humana.
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from typing import Any

import structlog
from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    merge_contextvars,
)


def _detect_json_default() -> bool:
    """Por defecto JSON en entornos no-TTY (CI, Docker, systemd)."""
    if os.environ.get("LOG_FORMAT", "").lower() == "json":
        return True
    if os.environ.get("LOG_FORMAT", "").lower() == "console":
        return False
    return not sys.stderr.isatty()


def configure_logging(
    *,
    level: str | int = "INFO",
    json_logs: bool | None = None,
) -> None:
    """Configura structlog + logging stdlib para toda la app.

    Idempotente: llamar múltiples veces es seguro.
    """
    if json_logs is None:
        json_logs = _detect_json_default()

    shared_processors: list[structlog.types.Processor] = [
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_logs:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirigir logs stdlib al formato estructurado
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_run_context(**kwargs: Any) -> str:
    """Asocia un correlation_id y otros campos al contexto del thread.

    Si no se pasa ``run_id``, se genera uno nuevo (uuid4). Devuelve el run_id.
    """
    run_id = kwargs.pop("run_id", None) or uuid.uuid4().hex[:12]
    bind_contextvars(run_id=run_id, **kwargs)
    return run_id


def clear_run_context() -> None:
    clear_contextvars()
