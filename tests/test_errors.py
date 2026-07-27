"""Global error handler: what reaches the user, and what reaches the admin."""
from __future__ import annotations

import pytest
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.methods import SendMessage
from aiogram.types import ErrorEvent, Update

from locales import get_texts
from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import make_bot, message_update

RU = get_texts("ru")


def _error_event(exception: Exception, bot=None) -> ErrorEvent:
    update: Update = message_update(USER_ID, "/start")
    if bot is not None:
        # Outside the dispatcher nothing is bound to a bot, so message.answer()
        # would raise before it ever reached the transport. Binding the Update
        # is not enough — the nested Message carries its own context.
        update.as_(bot)
        update.message.as_(bot)
    return ErrorEvent(update=update, exception=exception)


async def _run(exception: Exception):
    """Invoke the handler directly with a fresh bot, and report what was sent."""
    import importlib

    from handlers import errors

    importlib.reload(errors)
    bot, session = make_bot()

    # The alert throttle is module-level state; clear it between cases.
    from utils import notifier

    notifier._last_alert.clear()

    handled = await errors.on_error(_error_event(exception, bot), bot=bot)
    return handled, session


def _admin_messages(session) -> list[str]:
    return [
        str(call.data.get("text", ""))
        for call in session.calls_of("SendMessage")
        if call.data.get("chat_id") == ADMIN_ID
    ]


def _user_messages(session) -> list[str]:
    return [
        str(call.data.get("text", ""))
        for call in session.calls_of("SendMessage")
        if call.data.get("chat_id") == USER_ID
    ]


# ---------------------------------------------------------------- transient

async def test_network_error_is_not_escalated():
    """A dropped connection is an internet problem, not a bug worth an alert."""
    handled, session = await _run(
        TelegramNetworkError(method=SendMessage(chat_id=1, text="x"), message="WinError 121")
    )

    assert handled is True
    assert not _admin_messages(session), "network blips must not alert the admin"
    assert not _user_messages(session), "the user must not see a scary error"


async def test_blocked_user_is_not_escalated():
    handled, session = await _run(
        TelegramForbiddenError(
            method=SendMessage(chat_id=1, text="x"), message="bot was blocked"
        )
    )

    assert handled is True
    assert not _admin_messages(session)


async def test_flood_wait_is_not_escalated():
    handled, session = await _run(
        TelegramRetryAfter(
            method=SendMessage(chat_id=1, text="x"), message="flood", retry_after=5
        )
    )

    assert handled is True
    assert not _admin_messages(session)


# ---------------------------------------------------------------- real bugs

async def test_unexpected_error_reaches_the_user_and_the_admin():
    handled, session = await _run(ValueError("something genuinely broke"))

    assert handled is True

    user_texts = _user_messages(session)
    assert any(RU.GENERIC_ERROR.split("\n")[0] in text for text in user_texts)

    admin_texts = _admin_messages(session)
    assert admin_texts, "a real bug must alert the admin"
    assert "ValueError" in admin_texts[0]


async def test_admin_alert_is_throttled():
    """An error loop must not turn into an alert storm."""
    import importlib

    from handlers import errors
    from utils import notifier

    importlib.reload(errors)
    notifier._last_alert.clear()

    bot, session = make_bot()
    for _ in range(5):
        await errors.on_error(_error_event(ValueError("repeated"), bot), bot=bot)

    assert len(_admin_messages(session)) == 1


async def test_alert_does_not_leak_the_token():
    """A traceback must never carry a secret into a chat message."""
    from config import settings

    handled, session = await _run(RuntimeError(f"failed with {settings.bot.token}"))

    admin_texts = _admin_messages(session)
    assert admin_texts, "the alert should still be delivered"
    for text in admin_texts:
        assert settings.bot.token not in text
        assert "***BOT_TOKEN***" in text
