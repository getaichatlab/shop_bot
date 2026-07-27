"""A fake Telegram transport so handlers can be exercised without a network.

The dispatcher, routers, middlewares, FSM and database are all real — only the
HTTP call to api.telegram.org is replaced. Every outgoing API call is recorded
so tests can assert on what the bot tried to send.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import TelegramMethod
from aiogram.types import (
    CallbackQuery,
    Chat,
    Message,
    PreCheckoutQuery,
    SuccessfulPayment,
    Update,
    User,
)

BOT_ID = 424242
BOT_USERNAME = "test_shop_bot"


class RecordedCall:
    __slots__ = ("method", "data")

    def __init__(self, method: str, data: dict[str, Any]) -> None:
        self.method = method
        self.data = data

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.method} {self.data}>"


class MockedSession(BaseSession):
    """Returns plausible responses and records every request."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[RecordedCall] = []
        self._message_id = 1000

    # -- helpers ---------------------------------------------------------

    def calls_of(self, method: str) -> list[RecordedCall]:
        return [c for c in self.calls if c.method == method]

    def texts(self) -> list[str]:
        out: list[str] = []
        for call in self.calls:
            for key in ("text", "caption"):
                value = call.data.get(key)
                if value:
                    out.append(str(value))
        return out

    def said(self, needle: str) -> bool:
        return any(needle in text for text in self.texts())

    def clear(self) -> None:
        self.calls.clear()

    def _next_message(self, chat_id: int, text: str | None) -> Message:
        self._message_id += 1
        return Message(
            message_id=self._message_id,
            date=datetime.now(timezone.utc),
            chat=Chat(id=chat_id, type="private"),
            from_user=User(id=BOT_ID, is_bot=True, first_name="Bot", username=BOT_USERNAME),
            text=text,
        )

    # -- BaseSession API -------------------------------------------------

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None):
        name = type(method).__name__
        data = {k: v for k, v in method.model_dump(exclude_none=True).items()}
        self.calls.append(RecordedCall(name, data))

        if name == "GetMe":
            return User(
                id=BOT_ID, is_bot=True, first_name="Shop Bot", username=BOT_USERNAME
            )

        if name in {
            "SendMessage",
            "SendPhoto",
            "SendInvoice",
            "CopyMessage",
            "EditMessageText",
            "EditMessageCaption",
        }:
            chat_id = data.get("chat_id", 0)
            text = data.get("text") or data.get("caption")
            return self._next_message(int(chat_id) if chat_id else 0, text)

        # AnswerCallbackQuery, DeleteMessage, SetMyCommands, DeleteWebhook,
        # AnswerPreCheckoutQuery, SetWebhook ...
        return True

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def close(self) -> None:
        return None


def make_bot() -> tuple[Bot, MockedSession]:
    session = MockedSession()
    bot = Bot(
        token="424242:TEST-TOKEN",
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    return bot, session


# ---------------------------------------------------------------- updates

_update_id = 0
_msg_id = 0


def _next_update_id() -> int:
    global _update_id
    _update_id += 1
    return _update_id


def _next_msg_id() -> int:
    global _msg_id
    _msg_id += 1
    return _msg_id


def make_user(user_id: int, name: str = "Tester") -> User:
    return User(id=user_id, is_bot=False, first_name=name, username=f"u{user_id}")


def message_update(user_id: int, text: str) -> Update:
    user = make_user(user_id)
    return Update(
        update_id=_next_update_id(),
        message=Message(
            message_id=_next_msg_id(),
            date=datetime.now(timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=user,
            text=text,
        ),
    )


def contact_update(user_id: int, phone: str) -> Update:
    from aiogram.types import Contact

    user = make_user(user_id)
    return Update(
        update_id=_next_update_id(),
        message=Message(
            message_id=_next_msg_id(),
            date=datetime.now(timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=user,
            contact=Contact(phone_number=phone, first_name="Tester", user_id=user_id),
        ),
    )


def callback_update(user_id: int, data: str) -> Update:
    user = make_user(user_id)
    return Update(
        update_id=_next_update_id(),
        callback_query=CallbackQuery(
            id=f"cb{_next_update_id()}",
            from_user=user,
            chat_instance="ci",
            data=data,
            message=Message(
                message_id=_next_msg_id(),
                date=datetime.now(timezone.utc),
                chat=Chat(id=user_id, type="private"),
                from_user=User(id=BOT_ID, is_bot=True, first_name="Bot"),
                text="placeholder",
            ),
        ),
    )


def payment_update(
    user_id: int,
    payload: str,
    amount: int,
    charge_id: str = "CHARGE-1",
    currency: str = "UZS",
) -> Update:
    user = make_user(user_id)
    return Update(
        update_id=_next_update_id(),
        message=Message(
            message_id=_next_msg_id(),
            date=datetime.now(timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=user,
            successful_payment=SuccessfulPayment(
                currency=currency,
                total_amount=amount,
                invoice_payload=payload,
                telegram_payment_charge_id=charge_id,
                provider_payment_charge_id="prov-1",
            ),
        ),
    )


def pre_checkout_update(
    user_id: int, payload: str, amount: int, currency: str = "UZS"
) -> Update:
    return Update(
        update_id=_next_update_id(),
        pre_checkout_query=PreCheckoutQuery(
            id="pcq1",
            from_user=make_user(user_id),
            currency=currency,
            total_amount=amount,
            invoice_payload=payload,
        ),
    )
