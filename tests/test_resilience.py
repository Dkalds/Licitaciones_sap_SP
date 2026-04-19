"""Tests para scraper.resilience: retries y circuit breaker."""

from __future__ import annotations

import pybreaker
import pytest
import requests

from scraper.resilience import _is_transient, http_retry, placsp_breaker


class _FakeResp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_is_transient_connection_error():
    assert _is_transient(requests.ConnectionError("network down"))
    assert _is_transient(requests.Timeout("slow"))


def test_is_transient_http_5xx():
    err = requests.HTTPError()
    err.response = _FakeResp(503)
    assert _is_transient(err)


def test_is_transient_http_429():
    err = requests.HTTPError()
    err.response = _FakeResp(429)
    assert _is_transient(err)


def test_is_transient_http_4xx_not_retried():
    err = requests.HTTPError()
    err.response = _FakeResp(404)
    assert not _is_transient(err)


def test_is_transient_random_error_not_retried():
    assert not _is_transient(ValueError("payload too big"))


def test_http_retry_reraises_after_exhaustion():
    calls = {"n": 0}

    @http_retry
    def _boom():
        calls["n"] += 1
        raise requests.ConnectionError("down")

    with pytest.raises(requests.ConnectionError):
        _boom()
    # 4 intentos configurados en http_retry
    assert calls["n"] == 4


def test_http_retry_stops_on_non_transient():
    calls = {"n": 0}

    @http_retry
    def _boom():
        calls["n"] += 1
        raise ValueError("not transient")

    with pytest.raises(ValueError):
        _boom()
    assert calls["n"] == 1


def test_breaker_opens_after_consecutive_failures():
    # pybreaker abre el circuito cuando ``fail_counter >= fail_max`` y, en esa
    # misma llamada, lanza ``CircuitBreakerError`` en lugar de la original.
    local = pybreaker.CircuitBreaker(
        fail_max=3, reset_timeout=60, exclude=[ValueError], name="test_cb"
    )

    @local
    def always_fail():
        raise requests.ConnectionError("bad")

    with pytest.raises(requests.ConnectionError):
        always_fail()
    with pytest.raises(requests.ConnectionError):
        always_fail()
    # En la tercera llamada se alcanza fail_max=3 → el circuito se abre y el
    # error original se sustituye por ``CircuitBreakerError``.
    with pytest.raises(pybreaker.CircuitBreakerError):
        always_fail()
    # Llamadas posteriores también son cortocircuitadas.
    with pytest.raises(pybreaker.CircuitBreakerError):
        always_fail()


def test_placsp_breaker_exported():
    assert placsp_breaker.name == "placsp"
    assert placsp_breaker.fail_max == 5
