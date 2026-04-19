"""Tests para observability.logging."""

from __future__ import annotations

import json
import logging

import pytest

from observability.logging import (
    bind_run_context,
    clear_run_context,
    configure_logging,
    get_logger,
)


@pytest.fixture(autouse=True)
def _clear_ctx():
    clear_run_context()
    yield
    clear_run_context()


def test_configure_logging_is_idempotent():
    configure_logging(level="INFO", json_logs=True)
    configure_logging(level="INFO", json_logs=True)
    assert logging.getLogger().level == logging.INFO


def test_get_logger_returns_bound_logger():
    configure_logging(json_logs=True)
    log = get_logger("tests.obs")
    # structlog.get_logger devuelve un BoundLoggerLazyProxy;
    # lo importante es que exponga la API de logging.
    assert hasattr(log, "info")
    assert hasattr(log, "bind")


def test_bind_run_context_generates_run_id():
    run_id = bind_run_context()
    assert isinstance(run_id, str)
    assert len(run_id) == 12


def test_bind_run_context_respects_explicit_id():
    run_id = bind_run_context(run_id="fixed-id", module="tests")
    assert run_id == "fixed-id"


def test_json_logs_contain_run_id(capsys):
    configure_logging(level="INFO", json_logs=True)
    run_id = bind_run_context(run_id="r1", module="tests")
    log = get_logger("tests.json")
    log.info("test_event", foo="bar")
    captured = capsys.readouterr()
    # El output JSON va al stream stderr configurado por configure_logging.
    lines = [ln for ln in (captured.err + captured.out).splitlines() if "test_event" in ln]
    assert lines, "no se encontró el evento en stderr/stdout"
    # Buscamos una línea que sea JSON válido con run_id esperado.
    for ln in lines:
        try:
            data = json.loads(ln)
        except ValueError:
            continue
        if data.get("event") == "test_event":
            assert data["run_id"] == run_id
            assert data["foo"] == "bar"
            return
    pytest.fail(f"no JSON válido con event=test_event en: {lines}")
