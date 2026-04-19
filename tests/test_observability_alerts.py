"""Tests para observability.alerts."""

from __future__ import annotations

from unittest.mock import patch

from observability.alerts import AlertLevel, notify


def test_notify_below_min_level_is_noop(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "error")
    monkeypatch.delenv("ALERT_SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("ALERT_EMAIL_WEBHOOK_URL", raising=False)
    with (
        patch("observability.alerts._post_slack") as slack,
        patch("observability.alerts._post_email") as email,
    ):
        notify(AlertLevel.WARN, "t", "b")
    slack.assert_not_called()
    email.assert_not_called()


def test_notify_above_min_level_dispatches_slack(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "warn")
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK_URL", "https://hooks.slack.test/x")
    monkeypatch.delenv("ALERT_EMAIL_WEBHOOK_URL", raising=False)
    with patch("observability.alerts._post_slack") as slack:
        notify(AlertLevel.WARN, "t", "b", count=3)
    slack.assert_called_once()


def test_notify_dispatches_email_when_configured(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "info")
    monkeypatch.delenv("ALERT_SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("ALERT_EMAIL_WEBHOOK_URL", "https://mail.test/send")
    with patch("observability.alerts._post_email") as email:
        notify(AlertLevel.CRITICAL, "t", "b")
    email.assert_called_once()


def test_notify_accepts_string_level(monkeypatch):
    monkeypatch.setenv("ALERT_MIN_LEVEL", "warn")
    monkeypatch.delenv("ALERT_SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("ALERT_EMAIL_WEBHOOK_URL", raising=False)
    # No debe lanzar aun sin webhooks
    notify("error", "title", "body", foo="bar")


def test_alert_level_ordering():
    assert AlertLevel.INFO < AlertLevel.WARN < AlertLevel.ERROR < AlertLevel.CRITICAL
