"""Entry point: startup wiring only.

Supports both polling and webhook through a single .env switch (rule 3.8), and
shuts down gracefully on SIGTERM.
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat

from config import settings
from currencies import BASE_CURRENCY, CURRENCIES
from currencies import is_supported as currency_supported
from database import db
from handlers import build_router
from locales import LOCALES, get_texts
from middlewares import (
    ActivityMiddleware,
    EventLoggingMiddleware,
    I18nMiddleware,
    ThrottlingMiddleware,
)
from services.rates import ensure_seed_rates, rate_refresh_loop
from storage import SQLiteStorage
from utils.logger import setup_logging

log = logging.getLogger("bot")

# Set during shutdown so background tasks can exit cleanly.
_stop_event = asyncio.Event()


# ----------------------------------------------------------------- storage

def build_storage():
    """Pick the best FSM storage available, in order of preference.

    1. Redis, when REDIS_URL is set — the right answer under real concurrency.
    2. SQLite, in the same file as everything else — no extra service, and an
       unfinished checkout still survives a restart. This is the default.
    3. Memory, only if explicitly requested, and warned about.
    """
    if settings.use_redis:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            storage = RedisStorage.from_url(settings.redis_url)
            log.info("FSM storage: Redis")
            return storage
        except ImportError:
            log.error("redis package is missing — falling back to SQLite storage")

    if settings.fsm_storage == "memory":
        log.warning(
            "FSM storage: memory — unfinished checkout flows are lost on restart. "
            "Set FSM_STORAGE=sqlite to keep them."
        )
        return MemoryStorage()

    log.info("FSM storage: SQLite (%s)", settings.db_path)
    return SQLiteStorage(settings.db_path)


# ----------------------------------------------------------------- commands

COMMAND_DESCRIPTIONS = {
    "uz": {
        "start": "Botni ishga tushirish",
        "help": "Yordam",
        "language": "Tilni almashtirish",
        "currency": "Valyutani almashtirish",
        "cancel": "Amalni bekor qilish",
        "stats": "Statistika",
        "rates": "Valyuta kurslari",
    },
    "ru": {
        "start": "Запустить бота",
        "help": "Помощь",
        "language": "Сменить язык",
        "currency": "Сменить валюту",
        "cancel": "Отменить действие",
        "stats": "Статистика",
        "rates": "Курсы валют",
    },
}


def _commands(lang: str, with_stats: bool = False) -> list[BotCommand]:
    labels = COMMAND_DESCRIPTIONS.get(lang, COMMAND_DESCRIPTIONS["ru"])
    names = ["start", "help", "language", "currency", "cancel"]
    if with_stats:
        names += ["stats", "rates"]
    return [BotCommand(command=n, description=labels[n]) for n in names]


async def set_commands(bot: Bot) -> None:
    """Register the command menu, localized per Telegram client language."""
    # Default menu, used when the client language has no specific entry.
    await bot.set_my_commands(_commands(settings.default_lang))

    for lang in LOCALES:
        try:
            await bot.set_my_commands(_commands(lang), language_code=lang)
        except Exception as e:
            log.warning("Could not set commands for %s: %s", lang, e)

    # Admins additionally get /stats in their command menu.
    for admin_id in settings.bot.admin_ids:
        try:
            await bot.set_my_commands(
                _commands(settings.default_lang, with_stats=True),
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception as e:
            log.warning("Could not set admin commands for %s: %s", admin_id, e)


# ----------------------------------------------------------------- factory

def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=build_storage())

    # Middleware order: log -> throttle -> i18n -> activity.
    i18n = I18nMiddleware()
    for observer in (dp.message, dp.callback_query):
        observer.middleware(EventLoggingMiddleware())
        observer.middleware(ThrottlingMiddleware())
        observer.middleware(i18n)
        observer.middleware(ActivityMiddleware())

    # Pre-checkout queries need the locale too, but must never be throttled.
    dp.pre_checkout_query.middleware(i18n)

    dp.include_router(build_router())
    return dp


def create_bot() -> Bot:
    return Bot(
        token=settings.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


# ----------------------------------------------------------------- runners

def check_config() -> None:
    """Warn about settings that silently defeat localization."""
    if settings.payment.currency_symbol and len(LOCALES) > 1:
        variants = " / ".join(
            f"{code}:{get_texts(code).CURRENCY_SYMBOLS[BASE_CURRENCY]}"
            for code in LOCALES
        )
        log.warning(
            "CURRENCY_SYMBOL=%r overrides the per-language symbol, so every "
            "language will show it. Leave it empty in .env to use %s.",
            settings.payment.currency_symbol,
            variants,
        )

    if settings.default_lang not in LOCALES:
        log.warning(
            "DEFAULT_LANG=%r is not a shipped language (%s) — falling back.",
            settings.default_lang,
            ", ".join(LOCALES),
        )

    if not currency_supported(settings.default_currency):
        log.warning(
            "DEFAULT_CURRENCY=%r is not supported (%s) — falling back to %s.",
            settings.default_currency,
            ", ".join(CURRENCIES),
            BASE_CURRENCY,
        )

    if settings.payment.currency != BASE_CURRENCY:
        log.warning(
            "CURRENCY=%s differs from the accounting currency %s. Invoices are "
            "issued in %s, so these must match.",
            settings.payment.currency,
            BASE_CURRENCY,
            BASE_CURRENCY,
        )


async def on_startup(bot: Bot) -> None:
    check_config()
    await db.init_db()
    await ensure_seed_rates()
    await set_commands(bot)

    # Exchange rates refresh in the background; a slow or dead API must never
    # delay startup or block a single update.
    asyncio.create_task(rate_refresh_loop(_stop_event))
    me = await bot.get_me()
    log.info(
        "Bot started: @%s | admins=%s | payments=%s | mode=%s | languages=%s (default %s)",
        me.username,
        settings.bot.admin_ids,
        "on" if settings.payment.enabled else "off",
        "webhook" if settings.webhook.enabled else "polling",
        ",".join(LOCALES),
        settings.default_lang,
    )


async def run_polling() -> None:
    bot = create_bot()
    dp = create_dispatcher()
    dp.startup.register(on_startup)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, handle_signals=True)
    finally:
        await shutdown(bot, dp)


async def run_webhook() -> None:
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = create_bot()
    dp = create_dispatcher()
    dp.startup.register(on_startup)

    await db.init_db()
    await bot.set_webhook(
        url=f"{settings.webhook.base_url}{settings.webhook.path}",
        secret_token=settings.webhook.secret,
        drop_pending_updates=True,
    )
    log.info("Webhook registered at %s", settings.webhook.path)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook.secret,
    ).register(app, path=settings.webhook.path)
    setup_application(app, dp, bot=bot)

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.webhook.host, port=settings.webhook.port)
    await site.start()
    log.info("HTTP server listening on %s:%s", settings.webhook.host, settings.webhook.port)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass  # Windows

    try:
        await stop.wait()
    finally:
        await runner.cleanup()
        await shutdown(bot, dp)


async def shutdown(bot: Bot, dp: Dispatcher) -> None:
    """Graceful shutdown: close FSM storage and the HTTP session (rule 3.8)."""
    log.info("Shutting down...")
    _stop_event.set()
    try:
        await dp.storage.close()
    except Exception as e:
        log.warning("Storage close failed: %s", e)
    try:
        await bot.session.close()
    except Exception as e:
        log.warning("Session close failed: %s", e)
    log.info("Shutdown complete")


def main() -> None:
    setup_logging()
    runner = run_webhook if settings.webhook.enabled else run_polling
    try:
        asyncio.run(runner())
    except (KeyboardInterrupt, SystemExit):
        log.info("Stopped by signal")


if __name__ == "__main__":
    sys.exit(main())
