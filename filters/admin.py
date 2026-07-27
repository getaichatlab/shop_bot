"""Reusable admin filter (rule 3.2.4).

Admin ids come from config only — never hardcoded inside handler logic.
"""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import settings


def is_admin(user_id: int) -> bool:
    return user_id in settings.bot.admin_ids


class IsAdmin(BaseFilter):
    """Allow only configured admins."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return is_admin(user.id)


class IsPrivate(BaseFilter):
    """Restrict a handler to private chats."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        message = event if isinstance(event, Message) else event.message
        return bool(message and message.chat.type == "private")
