"""Safe outbound messaging: Telegram error handling + admin alerts with flood control."""
from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardMarkup

from config import settings
from utils.formatters import split_message
from utils.logger import redact_secrets
from utils.timing import NEVER

log = logging.getLogger(__name__)

# Rule 3.3: an error loop must never spam the admin.
_last_alert: dict[str, float] = {}


async def safe_send(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    retries: int = 1,
) -> bool:
    """Send a message, tolerating every common Telegram-side failure.

    Returns True if delivered. Never raises.
    """
    chunks = split_message(text)
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        attempt = 0
        while True:
            try:
                await bot.send_message(chat_id, chunk, reply_markup=markup)
                break
            except TelegramRetryAfter as e:
                # Flood control: respect the server-provided delay.
                if attempt >= retries:
                    log.warning("Flood limit for chat %s, giving up", chat_id)
                    return False
                attempt += 1
                log.warning("Flood wait %ss for chat %s", e.retry_after, chat_id)
                await asyncio.sleep(e.retry_after)
            except TelegramForbiddenError:
                # User blocked the bot or deleted the chat.
                log.info("Chat %s is unreachable (blocked/deleted)", chat_id)
                return False
            except TelegramBadRequest as e:
                log.warning("BadRequest for chat %s: %s", chat_id, e)
                return False
            except Exception as e:  # network hiccup, etc.
                log.warning("Send failed for chat %s: %s", chat_id, e)
                return False
    return True


async def safe_edit(
    message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Edit a message, ignoring 'message is not modified' and 'too old' errors."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        detail = str(e).lower()
        if "not modified" in detail:
            return True
        if "message to edit not found" in detail or "message can't be edited" in detail:
            log.debug("Message too old to edit")
            return False
        log.warning("Edit failed: %s", e)
        return False
    except Exception as e:
        log.warning("Edit failed: %s", e)
        return False


async def notify_admins(
    bot: Bot,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    prefer_orders_chat: bool = True,
) -> None:
    """Deliver a message to the orders chat, or to every admin as a fallback."""
    if prefer_orders_chat and settings.bot.orders_chat_id:
        targets = [settings.bot.orders_chat_id]
    else:
        targets = settings.bot.admin_ids
    for chat_id in targets:
        await safe_send(bot, chat_id, text, reply_markup)


async def alert_admins(bot: Bot, key: str, text: str) -> None:
    """Critical-error alert, throttled per error key to avoid an alert storm.

    The text is redacted first: an exception message can carry the bot token
    (a failed API call includes the URL), and that must never reach a chat.
    """
    now = time.monotonic()
    # NEVER, not 0.0: on a machine that booted a minute ago, 0.0 would read as
    # "alerted just now" and the very first alert would be swallowed.
    last = _last_alert.get(key, NEVER)
    if now - last < settings.admin_error_cooldown:
        return
    _last_alert[key] = now

    safe_text = redact_secrets(text)
    for admin_id in settings.bot.admin_ids:
        await safe_send(bot, admin_id, safe_text)
