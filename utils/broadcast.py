"""Throttled broadcast queue.

Telegram allows roughly 30 messages/second overall. We stay well under that and
back off automatically when the server asks us to (rule 3.4).
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

log = logging.getLogger(__name__)

MESSAGES_PER_SECOND = 20          # safety margin below Telegram's ~30/s
DELAY = 1 / MESSAGES_PER_SECOND


@dataclass
class BroadcastResult:
    sent: int = 0
    failed: int = 0
    blocked: int = 0
    seconds: float = 0.0


async def broadcast_copy(
    bot: Bot,
    user_ids: list[int],
    from_chat_id: int,
    message_id: int,
    *,
    on_blocked=None,
) -> BroadcastResult:
    """Copy one message to many users at a safe rate.

    `on_blocked` is an optional async callback invoked with the user_id of anyone
    who has blocked the bot, so the caller can deactivate them in the database.
    """
    result = BroadcastResult()
    started = time.monotonic()

    for user_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            result.sent += 1
        except TelegramRetryAfter as e:
            log.warning("Broadcast flood wait: %ss", e.retry_after)
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
                result.sent += 1
            except Exception:
                result.failed += 1
        except TelegramForbiddenError:
            result.blocked += 1
            result.failed += 1
            if on_blocked is not None:
                try:
                    await on_blocked(user_id)
                except Exception:
                    log.debug("on_blocked callback failed for %s", user_id)
        except TelegramBadRequest as e:
            log.debug("Broadcast bad request for %s: %s", user_id, e)
            result.failed += 1
        except Exception as e:
            log.warning("Broadcast failed for %s: %s", user_id, e)
            result.failed += 1

        await asyncio.sleep(DELAY)

    result.seconds = round(time.monotonic() - started, 1)
    return result
