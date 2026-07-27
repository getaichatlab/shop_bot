"""Global error handler (rule 3.3).

The user always sees a friendly message in their own language; the admin gets a
throttled alert; the full traceback goes to the log only.
"""
from __future__ import annotations

import logging
from types import ModuleType

from aiogram import Bot, Router
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.types import ErrorEvent, Message

from config import settings
from locales import get_texts
from utils.formatters import esc
from utils.notifier import alert_admins

router = Router(name="errors")
log = logging.getLogger("errors")

MAX_ALERT_CHARS = 300

admin_texts = get_texts(settings.default_lang)


@router.errors()
async def on_error(event: ErrorEvent, bot: Bot, **data) -> bool:
    exception = event.exception

    # Expected Telegram conditions — logged, never escalated to the admin.
    if isinstance(exception, TelegramForbiddenError):
        log.info("User unreachable: %s", exception)
        return True
    if isinstance(exception, TelegramRetryAfter):
        log.warning("Flood control: retry after %ss", exception.retry_after)
        return True
    if isinstance(exception, TelegramNetworkError):
        # The connection to api.telegram.org dropped mid-request: a bad link, a
        # flaky VPN, a DNS hiccup. Nothing is wrong with the bot, and aiogram
        # will retry the next update on its own. Alerting the admin on every
        # network blip would train them to ignore the alerts that matter.
        log.warning("Network error talking to Telegram: %s", exception)
        return True

    # The i18n middleware may not have run if the failure happened early.
    t: ModuleType = data.get("t") or admin_texts

    update = event.update
    where = "unknown"
    target: Message | None = None

    if update.message is not None:
        target = update.message
        detail = (
            update.message.text[:32]
            if update.message.text
            else update.message.content_type
        )
        where = f"message:{detail}"
    elif update.callback_query is not None:
        target = update.callback_query.message
        where = f"callback:{update.callback_query.data}"

    log.exception("Unhandled error in %s: %s", where, exception)

    # Friendly message to the user.
    try:
        if update.callback_query is not None:
            await update.callback_query.answer(t.GENERIC_ERROR, show_alert=True)
        elif target is not None:
            await target.answer(t.GENERIC_ERROR)
    except Exception:
        log.debug("Could not deliver the error message to the user")

    # Throttled alert to admins.
    await alert_admins(
        bot,
        key=type(exception).__name__,
        text=admin_texts.ADMIN_ERROR_ALERT.format(
            error_type=esc(type(exception).__name__),
            where=esc(where),
            message=esc(str(exception)[:MAX_ALERT_CHARS]),
        ),
    )
    return True
