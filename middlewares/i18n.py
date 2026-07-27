"""Injects the caller's locale into every handler.

Handlers receive `t` (the locale module) and `lang` (its code) and never import
a specific language themselves.

Language resolution order:
  1. the language stored in the database for this user
  2. the Telegram client language, if we support it (first contact only)
  3. `DEFAULT_LANG` from .env
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from config import settings
from currencies import BASE_CURRENCY
from currencies import is_supported as currency_supported
from database import db
from locales import get_texts, is_supported

log = logging.getLogger(__name__)


class I18nMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        # user_id -> (language, currency). Saves a query on every single update.
        self._cache: dict[int, tuple[str, str]] = {}

    def invalidate(self, user_id: int) -> None:
        self._cache.pop(user_id, None)

    def remember(self, user_id: int, lang: str | None = None,
                 currency: str | None = None) -> None:
        current = self._cache.get(user_id)
        base_lang = current[0] if current else settings.default_lang
        base_currency = current[1] if current else BASE_CURRENCY
        self._cache[user_id] = (lang or base_lang, currency or base_currency)

    async def _resolve(
        self, user_id: int, client_lang: str | None
    ) -> tuple[str, str]:
        cached = self._cache.get(user_id)
        if cached:
            return cached

        try:
            stored_lang = await db.get_user_language(user_id)
            stored_currency = await db.get_user_currency(user_id)
        except Exception as e:
            log.debug("Preference lookup failed for %s: %s", user_id, e)
            stored_lang = stored_currency = None

        if is_supported(stored_lang):
            lang = stored_lang  # type: ignore[assignment]
        elif is_supported(client_lang):
            lang = client_lang  # type: ignore[assignment]
        else:
            lang = settings.default_lang
        if not is_supported(lang):
            lang = "ru"

        currency = (
            stored_currency
            if currency_supported(stored_currency)
            else settings.default_currency
        )
        if not currency_supported(currency):
            currency = BASE_CURRENCY

        self._cache[user_id] = (lang, currency)
        return lang, currency

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")

        if user is None:
            lang, currency = settings.default_lang, settings.default_currency
        else:
            lang, currency = await self._resolve(
                user.id, getattr(user, "language_code", None)
            )

        data["lang"] = lang
        data["currency"] = currency
        data["t"] = get_texts(lang)
        data["i18n"] = self
        return await handler(event, data)
