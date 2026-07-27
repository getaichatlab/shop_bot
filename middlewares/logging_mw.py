"""Structured event logging. Never logs message content that could be sensitive."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

log = logging.getLogger("events")


class EventLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        user_id = user.id if user else "?"

        if isinstance(event, CallbackQuery):
            # callback_data is bot-generated and safe to log.
            log.info("callback user=%s data=%s", user_id, event.data)
        elif isinstance(event, Message):
            if event.successful_payment:
                log.info("payment user=%s", user_id)
            elif event.content_type != "text":
                log.info("message user=%s type=%s", user_id, event.content_type)
            else:
                # Log only the length, never the text itself.
                log.info("message user=%s len=%s", user_id, len(event.text or ""))

        return await handler(event, data)
