"""Tests para observability.alerts (envío SMTP directo)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from observability.alerts import AlertLevel, _build_html, notify


def test_notify_below_min_level_is_noop(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "error")
    with patch("observability.alerts._send_smtp") as smtp:
        notify(AlertLevel.WARN, "t", "b")
    smtp.assert_not_called()


def test_notify_above_min_level_calls_smtp(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "warn")
    with patch("observability.alerts._send_smtp") as smtp:
        notify(AlertLevel.WARN, "título", "cuerpo", count=3)
    smtp.assert_called_once()
    args = smtp.call_args[0]
    assert args[0] == AlertLevel.WARN
    assert args[1] == "título"


def test_notify_critical_always_dispatched(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "warn")
    with patch("observability.alerts._send_smtp") as smtp:
        notify(AlertLevel.CRITICAL, "alerta crítica")
    smtp.assert_called_once()


def test_notify_accepts_string_level(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "warn")
    with patch("observability.alerts._send_smtp") as smtp:
        notify("error", "title", "body", foo="bar")
    smtp.assert_called_once()


def test_notify_unknown_string_level_defaults_to_warn(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "info")
    with patch("observability.alerts._send_smtp") as smtp:
        notify("unknown_level", "title")
    smtp.assert_called_once()


def test_alert_level_ordering():
    assert AlertLevel.INFO < AlertLevel.WARN < AlertLevel.ERROR < AlertLevel.CRITICAL


def test_send_smtp_skips_when_not_configured(monkeypatch):
    """Sin variables de entorno SMTP no intenta conectar."""
    monkeypatch.delenv("ALERT_EMAIL_TO", raising=False)
    monkeypatch.delenv("ALERT_SMTP_USER", raising=False)
    monkeypatch.delenv("ALERT_SMTP_PASSWORD", raising=False)
    with patch("smtplib.SMTP") as mock_smtp:
        from observability.alerts import _send_smtp

        _send_smtp(AlertLevel.WARN, "t", "b", {})
    mock_smtp.assert_not_called()


def test_send_smtp_connects_and_sends(monkeypatch):
    """Con credenciales configuradas se conecta al servidor SMTP."""
    monkeypatch.setenv("ALERT_EMAIL_TO", "dest@example.com")
    monkeypatch.setenv("ALERT_SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("ALERT_SMTP_PASSWORD", "app-password-16ch")
    monkeypatch.setenv("ALERT_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("ALERT_SMTP_PORT", "587")

    mock_server = MagicMock()
    mock_server.__enter__ = lambda s: s
    mock_server.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_server):
        from observability.alerts import _send_smtp

        _send_smtp(AlertLevel.ERROR, "Test error", "algo falló", {"run_id": "abc"})

    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("sender@gmail.com", "app-password-16ch")
    mock_server.sendmail.assert_called_once()
    # Verifica que el destinatario es el correcto
    _, call_args, _ = mock_server.sendmail.mock_calls[0]
    assert "dest@example.com" in call_args[1]


def test_build_html_contains_title_and_body():
    html = _build_html(AlertLevel.ERROR, "Mi título", "Descripción del error", {"run": "r1"})
    assert "Mi título" in html
    assert "Descripción del error" in html
    assert "run" in html
    assert "r1" in html


def test_build_html_uses_level_color():
    html_warn = _build_html(AlertLevel.WARN, "t", "b", {})
    html_crit = _build_html(AlertLevel.CRITICAL, "t", "b", {})
    assert "#e6a817" in html_warn  # color WARN
    assert "#8b0000" in html_crit  # color CRITICAL
