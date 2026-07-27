"""Per-user rate limiting (rule 3.2.5).

A lightweight in-memory TTL cache keyed by user id. Admins are exempt so an
admin flow (broadcast, product upload) is never blocked.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import settings
from filters.admin import is_admin
from locales import get_texts

log = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Drop events that arrive faster than `rate` seconds apart, per user."""

    def __init__(self, rate: float | None = None, cleanup_after: int = 600) -> None:
        self.rate = rate if rate is not None else settings.throttle_rate
        self.cleanup_after = cleanup_after
        self._last_seen: dict[int, float] = {}
        self._warned: dict[int, float] = {}
        self._last_cleanup = time.monotonic()

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self.cleanup_after:
            return
        cutoff = now - self.cleanup_after
        self._last_seen = {k: v for k, v in self._last_seen.items() if v > cutoff}
        self._warned = {k: v for k, v in self._warned.items() if v > cutoff}
        self._last_cleanup = now

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or is_admin(user.id):
            return await handler(event, data)

        now = time.monotonic()
        self._cleanup(now)

        last = self._last_seen.get(user.id, 0.0)
        if now - last < self.rate:
            # Warn at most once every 3 seconds so we don't spam back.
            if now - self._warned.get(user.id, 0.0) > 3:
                self._warned[user.id] = now
                # This middleware runs before i18n, so resolve the locale from
                # the Telegram client language with the configured fallback.
                t = get_texts(getattr(user, "language_code", None) or settings.default_lang)
                try:
                    if isinstance(event, CallbackQuery):
                        await event.answer(t.THROTTLED, show_alert=False)
                    elif isinstance(event, Message):
                        await event.answer(t.THROTTLED)
                except Exception:
                    log.debug("Throttle notice could not be delivered")
            return None

        self._last_seen[user.id] = now
        return await handler(event, data)
