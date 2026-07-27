"""Keeps `users.last_seen` fresh for the active-users metric (rule 3.9).

The DB write is throttled in memory so a chatty user does not cause a write per
message.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import db
from utils.timing import NEVER

log = logging.getLogger(__name__)

TOUCH_INTERVAL = 300  # seconds


class ActivityMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._touched: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            # NEVER, not 0.0 — otherwise nobody is recorded as seen during the
            # first five minutes of uptime.
            if now - self._touched.get(user.id, NEVER) > TOUCH_INTERVAL:
                self._touched[user.id] = now
                try:
                    await db.touch_user(user.id)
                except Exception as e:
                    log.debug("touch_user failed: %s", e)
        return await handler(event, data)
