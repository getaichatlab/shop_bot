"""Formatting helpers: money, timestamps, HTML escaping, long-message splitting."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from types import ModuleType
from zoneinfo import ZoneInfo

from config import settings
from currencies import BASE_CURRENCY
from locales import get_texts
from utils.validators import MAX_MESSAGE_LEN

_TZ = ZoneInfo(settings.timezone)


def fmt_price(value: int, t: ModuleType | None = None) -> str:
    """Format an amount in the BASE currency.

    Customer-facing prices go through utils.money.price_text instead, which also
    handles the display currency. This helper is for admin views and totals,
    which always stay in the accounting currency.

    `CURRENCY_SYMBOL` in .env overrides the per-language symbol — useful when
    the base currency's name does not need translating (USD, EUR).
    """
    from utils.money import format_amount

    locale = t if t is not None else get_texts(None)
    override = settings.payment.currency_symbol
    if override:
        amount = f"{value:,}".replace(",", " ")
        return f"{amount} {override}"
    return format_amount(value, BASE_CURRENCY, locale)


def esc(value: object) -> str:
    """Escape user-generated content before embedding it into HTML parse_mode."""
    return html.escape(str(value), quote=False)


def to_local(value: str | datetime | None) -> datetime | None:
    """DB stores UTC. Convert to the configured display timezone."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ)


def fmt_dt(value: str | datetime | None) -> str:
    local = to_local(value)
    return local.strftime("%d.%m.%Y %H:%M") if local else "—"


def split_message(text: str, limit: int = MAX_MESSAGE_LEN) -> list[str]:
    """Split a long message on line boundaries so Telegram never rejects it."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        # A single line longer than the limit must be hard-split.
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
