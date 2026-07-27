"""Behaviour during the first minutes of a machine's uptime.

`time.monotonic()` counts from boot, so on a freshly started server it returns a
small number. Code that used `0.0` to mean "this has never happened" therefore
read every cooldown as *already elapsed a moment ago* and suppressed the first
event of each kind.

This is not theoretical: it is exactly what broke seven tests on a GitHub
runner, which boots seconds before the suite runs. It would equally have
swallowed the first admin alert on a freshly deployed bot — the one alert that
matters most.

Every test here pins `time.monotonic` to a small value, the way a machine that
booted forty seconds ago would report it.
"""
from __future__ import annotations

import pytest

from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import make_bot, message_update
from utils.timing import NEVER

# A machine that came up forty seconds ago.
JUST_BOOTED = 40.0


def _freeze(monkeypatch, module, value: float = JUST_BOOTED) -> None:
    """Make `module.time.monotonic()` report a freshly booted clock."""
    monkeypatch.setattr(module.time, "monotonic", lambda: value)


# ---------------------------------------------------------------- the sentinel

def test_never_is_older_than_any_cooldown() -> None:
    for cooldown in (0.5, 3, 300, 10**9):
        assert JUST_BOOTED - NEVER > cooldown
    assert not (JUST_BOOTED - NEVER < 1), "NEVER must never look recent"


# ---------------------------------------------------------------- rate cache

async def test_rate_cache_can_be_invalidated_on_a_fresh_machine(clean_db, monkeypatch):
    """`invalidate()` must drop the cache whatever the clock says."""
    import services.rates as rates_module

    db = clean_db
    _freeze(monkeypatch, rates_module)

    provider = rates_module.RateProvider()
    await db.set_rate("USD", 12000.0)
    assert await provider.get("USD") == pytest.approx(12000.0)

    await db.set_rate("USD", 13000.0)
    provider.invalidate()

    assert await provider.get("USD") == pytest.approx(13000.0), (
        "the cache survived invalidate() — uptime must not decide this"
    )


async def test_a_fresh_provider_reads_the_database(clean_db, monkeypatch):
    """A provider built at start-up has no rates and must not pretend it has."""
    import services.rates as rates_module

    db = clean_db
    _freeze(monkeypatch, rates_module)

    await db.set_rate("USD", 12345.0)
    provider = rates_module.RateProvider()

    assert await provider.get("USD") == pytest.approx(12345.0)


# ---------------------------------------------------------------- admin alerts

async def test_the_first_admin_alert_is_delivered_right_after_boot(monkeypatch):
    """The alert a fresh deploy needs most must not be eaten by the throttle."""
    from utils import notifier

    _freeze(monkeypatch, notifier)
    notifier._last_alert.clear()

    bot, session = make_bot()
    await notifier.alert_admins(bot, "boot-key", "ValueError: something broke")

    sent = [
        call for call in session.calls_of("SendMessage")
        if call.data.get("chat_id") == ADMIN_ID
    ]
    assert sent, "the first alert after boot was suppressed"


async def test_the_second_alert_is_still_throttled_after_boot(monkeypatch):
    """The fix must not remove the flood control it sits inside."""
    from utils import notifier

    _freeze(monkeypatch, notifier)
    notifier._last_alert.clear()

    bot, session = make_bot()
    for _ in range(4):
        await notifier.alert_admins(bot, "storm-key", "ValueError: repeated")

    sent = [
        call for call in session.calls_of("SendMessage")
        if call.data.get("chat_id") == ADMIN_ID
    ]
    assert len(sent) == 1, "the throttle stopped working"


# ---------------------------------------------------------------- middlewares

async def test_last_seen_is_recorded_right_after_boot(monkeypatch):
    """Otherwise the active-user metric is blind for the first five minutes."""
    import middlewares.activity as activity_module

    _freeze(monkeypatch, activity_module)

    middleware = activity_module.ActivityMiddleware()
    touched: list[int] = []

    async def fake_touch(user_id: int) -> None:
        touched.append(user_id)

    monkeypatch.setattr(activity_module.db, "touch_user", fake_touch)

    update = message_update(USER_ID, "/start")

    async def handler(event, data):
        return None

    await middleware(handler, update, {"event_from_user": update.message.from_user})

    assert touched == [USER_ID], "a fresh boot hid the user from last_seen"


async def test_a_first_message_is_not_throttled_after_boot(monkeypatch):
    """A brand-new user must be served, not rate-limited by an empty cache."""
    import middlewares.throttling as throttling_module

    # The throttle window is sub-second, so only the very first moments of
    # uptime are at risk — pin the clock there.
    _freeze(monkeypatch, throttling_module, 0.2)

    middleware = throttling_module.ThrottlingMiddleware(rate=0.5)
    update = message_update(USER_ID, "/start")
    passed: list[bool] = []

    async def handler(event, data):
        passed.append(True)
        return "handled"

    result = await middleware(
        handler, update, {"event_from_user": update.message.from_user}
    )

    assert passed == [True], "the very first message was throttled"
    assert result == "handled"
