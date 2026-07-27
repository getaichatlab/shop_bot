"""Logging setup with rotation so logs/ never grows unbounded (rule 3.9)."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import settings

def redact_secrets(text: str) -> str:
    """Replace every configured secret with a placeholder.

    Used for log records *and* for anything sent to a chat: an exception message
    can easily carry the token (a failed HTTP call includes the API URL), and a
    token pasted into an admin chat is far worse than one in a log file.
    """
    if not text:
        return text

    for value, placeholder in (
        (settings.bot.token, "***BOT_TOKEN***"),
        (settings.payment.provider_token, "***PROVIDER_TOKEN***"),
        (settings.webhook.secret, "***WEBHOOK_SECRET***"),
    ):
        if value and value in text:
            text = text.replace(value, placeholder)

    return text


class SecretFilter(logging.Filter):
    """Rule 3.2.9: logs must never contain secrets."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = redact_secrets(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging() -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(fmt)

    file_handler = RotatingFileHandler(
        log_dir / "bot.log",
        maxBytes=5 * 1024 * 1024,   # 5 MB per file
        backupCount=5,              # keep 5 rotations -> 30 MB ceiling
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    secret_filter = SecretFilter()
    console.addFilter(secret_filter)
    file_handler.addFilter(secret_filter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    # aiohttp access logs are noisy in webhook mode
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
