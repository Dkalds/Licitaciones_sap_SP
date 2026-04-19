"""Envío de alertas a Slack/email/console según entorno.

Configura con variables de entorno:

- ``ALERT_SLACK_WEBHOOK_URL``: URL del webhook entrante de Slack.
- ``ALERT_EMAIL_WEBHOOK_URL``: endpoint HTTP que recibe POST JSON con ``subject``
  y ``body``. Útil si usas un relay SMTP/serverless (e.g. Resend, Mailgun).
- ``ALERT_MIN_LEVEL``: ``info`` | ``warn`` | ``error`` (default ``warn``).

Si no hay webhooks configurados, las alertas se escriben al log estructurado.
"""

from __future__ import annotations

import os
from enum import IntEnum
from typing import Any

import requests

from observability.logging import get_logger

log = get_logger(__name__)


class AlertLevel(IntEnum):
    INFO = 10
    WARN = 20
    ERROR = 30
    CRITICAL = 40


_LEVEL_NAMES = {
    "info": AlertLevel.INFO,
    "warn": AlertLevel.WARN,
    "warning": AlertLevel.WARN,
    "error": AlertLevel.ERROR,
    "critical": AlertLevel.CRITICAL,
}


def _min_level() -> AlertLevel:
    raw = os.environ.get("ALERT_MIN_LEVEL", "warn").lower()
    return _LEVEL_NAMES.get(raw, AlertLevel.WARN)


def _emoji(level: AlertLevel) -> str:
    return {
        AlertLevel.INFO: ":information_source:",
        AlertLevel.WARN: ":warning:",
        AlertLevel.ERROR: ":x:",
        AlertLevel.CRITICAL: ":rotating_light:",
    }[level]


def _post_slack(
    url: str, level: AlertLevel, title: str, body: str, context: dict[str, Any]
) -> None:
    payload = {
        "text": f"{_emoji(level)} *{title}*",
        "attachments": [
            {
                "color": {
                    AlertLevel.INFO: "#36a64f",
                    AlertLevel.WARN: "#ffb347",
                    AlertLevel.ERROR: "#e04e4e",
                    AlertLevel.CRITICAL: "#8b0000",
                }[level],
                "text": body,
                "fields": [
                    {"title": k, "value": str(v), "short": True} for k, v in context.items()
                ],
            }
        ],
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning("alert_slack_failed", error=str(e))


def _post_email(
    url: str, level: AlertLevel, title: str, body: str, context: dict[str, Any]
) -> None:
    payload = {
        "subject": f"[{level.name}] {title}",
        "body": body,
        "context": context,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning("alert_email_failed", error=str(e))


def notify(
    level: AlertLevel | str,
    title: str,
    body: str = "",
    **context: Any,
) -> None:
    """Envía una alerta. Seguro de llamar sin configuración (loguea).

    ``level`` puede ser un enum ``AlertLevel`` o una cadena (``info``/``warn``/
    ``error``/``critical``).
    """
    if isinstance(level, str):
        level = _LEVEL_NAMES.get(level.lower(), AlertLevel.WARN)

    if level < _min_level():
        return

    log.log(
        {
            AlertLevel.INFO: 20,
            AlertLevel.WARN: 30,
            AlertLevel.ERROR: 40,
            AlertLevel.CRITICAL: 50,
        }[level],
        "alert",
        alert_title=title,
        alert_body=body,
        **context,
    )

    slack_url = os.environ.get("ALERT_SLACK_WEBHOOK_URL", "").strip()
    email_url = os.environ.get("ALERT_EMAIL_WEBHOOK_URL", "").strip()

    if slack_url:
        _post_slack(slack_url, level, title, body, context)
    if email_url:
        _post_email(email_url, level, title, body, context)
