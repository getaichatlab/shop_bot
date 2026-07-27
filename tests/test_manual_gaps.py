"""Cases that used to live only in the manual checklist.

Everything here was previously "click it yourself and see" — photo upload,
delivery to a group chat, keyboard layout, throttling. Automating them is what
turns the checklist from a promise into a guarantee.
"""
from __future__ import annotations

import pytest

from currencies import CURRENCY_ORDER
from locales import LOCALES, get_texts
from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import callback_update, make_user, message_update
from tests.test_flow import build, feed, head

RU = get_texts("ru")
UZ = get_texts("uz")
SKIP_WORD = "нет"


def photo_update(user_id: int, file_id: str = "AgACPHOTO123"):
    """A real Telegram photo message: several sizes, largest last."""
    from datetime import datetime, timezone

    from aiogram.types import Chat, Message, PhotoSize, Update

    from tests.mocks import _next_msg_id, _next_update_id

    sizes = [
        PhotoSize(file_id=f"{file_id}_s", file_unique_id="u1", width=90, height=90, file_size=1000),
        PhotoSize(file_id=f"{file_id}_m", file_unique_id="u2", width=320, height=320, file_size=8000),
        PhotoSize(file_id=file_id, file_unique_id="u3", width=1280, height=1280, file_size=90000),
    ]
    return Update(
        update_id=_next_update_id(),
        message=Message(
            message_id=_next_msg_id(),
            date=datetime.now(timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=make_user(user_id),
            photo=sizes,
        ),
    )


# ---------------------------------------------------------------- photos

async def _add_product_with(dp, bot, db, photo_step) -> None:
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))
    await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_ADD_PRODUCT))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    await feed(dp, bot, callback_update(ADMIN_ID, f"acat:{cat_id}"))
    await feed(dp, bot, message_update(ADMIN_ID, "Товар с фото"))
    await feed(dp, bot, message_update(ADMIN_ID, "Rasmli mahsulot"))
    await feed(dp, bot, message_update(ADMIN_ID, "Описание"))
    await feed(dp, bot, message_update(ADMIN_ID, "Tavsif"))
    await feed(dp, bot, message_update(ADMIN_ID, "500 000"))
    # One price prompt per extra currency.
    for _ in CURRENCY_ORDER[1:]:
        await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_PRICE_AUTO))
    await photo_step()


async def test_admin_can_attach_a_photo(clean_db):
    """The largest size must be stored — that is the one worth showing."""
    db = clean_db
    bot, session, dp = await build()

    await _add_product_with(
        dp, bot, db, lambda: feed(dp, bot, photo_update(ADMIN_ID, "PHOTO_LARGE"))
    )

    cat_id = (await db.get_categories("ru"))[0]["id"]
    added = [p for p in await db.get_products(cat_id, "ru") if p["title"] == "Товар с фото"]
    assert added, "the product was not created"
    assert added[0]["photo_id"] == "PHOTO_LARGE"


async def test_product_with_a_photo_is_sent_as_a_photo(clean_db):
    db = clean_db
    bot, session, dp = await build()

    await _add_product_with(
        dp, bot, db, lambda: feed(dp, bot, photo_update(ADMIN_ID, "PHOTO_LARGE"))
    )

    cat_id = (await db.get_categories("ru"))[0]["id"]
    product = [
        p for p in await db.get_products(cat_id, "ru") if p["title"] == "Товар с фото"
    ][0]

    await feed(dp, bot, message_update(USER_ID, "/start"))
    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"prd:{product['id']}:{cat_id}"))

    photos = session.calls_of("SendPhoto")
    assert photos, "a product with a photo must be sent as a photo message"
    assert photos[-1].data["photo"] == "PHOTO_LARGE"
    assert "Товар с фото" in str(photos[-1].data.get("caption", ""))


async def test_product_without_a_photo_is_sent_as_text(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    product = (await db.get_products(cat_id, "ru"))[0]

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"prd:{product['id']}:{cat_id}"))

    assert not session.calls_of("SendPhoto")
    assert session.said(product["title"])


async def test_a_photo_sent_at_the_wrong_moment_is_rejected(clean_db):
    """Sending a photo where a name is expected must not corrupt the flow."""
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))
    await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_ADD_CATEGORY))

    session.clear()
    await feed(dp, bot, photo_update(ADMIN_ID))

    assert not await db.get_categories("ru") == [], "catalog should be untouched"
    titles = [c["title"] for c in await db.get_categories("ru")]
    assert "Смартфоны" in titles


# ---------------------------------------------------------------- group chat

async def test_orders_go_to_the_group_when_configured(clean_db, monkeypatch):
    """With ORDERS_CHAT_ID set, admins must not also be DMed."""
    import dataclasses

    from config import settings
    from utils import notifier

    group_id = -1001234567890
    # Settings is frozen by design, so build a modified copy and point the
    # notifier at it for the duration of the test.
    patched = dataclasses.replace(
        settings, bot=dataclasses.replace(settings.bot, orders_chat_id=group_id)
    )
    monkeypatch.setattr(notifier, "settings", patched)

    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, message_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))

    targets = {c.data.get("chat_id") for c in session.calls_of("SendMessage")}
    assert group_id in targets, "the group did not receive the order"
    assert ADMIN_ID not in targets, "admins should not be DMed as well"


# ---------------------------------------------------------------- keyboards

async def test_main_menu_layout(clean_db):
    """Every advertised button is actually on the keyboard."""
    bot, session, dp = await build()
    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    keyboard = None
    for call in session.calls_of("SendMessage"):
        markup = call.data.get("reply_markup")
        if isinstance(markup, dict) and markup.get("keyboard"):
            keyboard = markup["keyboard"]
    assert keyboard, "no reply keyboard was sent"

    labels = {b["text"] if isinstance(b, dict) else b for row in keyboard for b in row}
    for expected in (
        RU.BTN_CATALOG,
        RU.BTN_CART,
        RU.BTN_MY_ORDERS,
        RU.BTN_CONTACTS,
        RU.BTN_LANGUAGE,
        RU.BTN_CURRENCY,
    ):
        assert expected in labels, f"missing button: {expected}"

    assert RU.BTN_ADMIN not in labels, "a plain user must not see the admin button"


async def test_admin_menu_has_the_admin_button(clean_db):
    bot, session, dp = await build()
    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))

    labels = set()
    for call in session.calls_of("SendMessage"):
        markup = call.data.get("reply_markup")
        if isinstance(markup, dict) and markup.get("keyboard"):
            labels |= {
                b["text"] if isinstance(b, dict) else b
                for row in markup["keyboard"]
                for b in row
            }
    assert RU.BTN_ADMIN in labels


async def test_admin_panel_layout(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_ADMIN))

    labels = set()
    for call in session.calls_of("SendMessage"):
        markup = call.data.get("reply_markup")
        if isinstance(markup, dict) and markup.get("keyboard"):
            labels |= {
                b["text"] if isinstance(b, dict) else b
                for row in markup["keyboard"]
                for b in row
            }

    for expected in (
        RU.BTN_ADD_PRODUCT,
        RU.BTN_ADD_CATEGORY,
        RU.BTN_ORDERS,
        RU.BTN_STATS,
        RU.BTN_RATES,
        RU.BTN_BROADCAST,
    ):
        assert expected in labels, f"missing admin button: {expected}"


async def test_phone_step_offers_the_contact_button(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))

    requests_contact = False
    for call in session.calls_of("SendMessage"):
        markup = call.data.get("reply_markup")
        if isinstance(markup, dict):
            for row in markup.get("keyboard", []) or []:
                for button in row:
                    if isinstance(button, dict) and button.get("request_contact"):
                        requests_contact = True
    assert requests_contact, "the phone step must offer a one-tap contact button"


# ---------------------------------------------------------------- throttling

async def test_throttling_blocks_a_burst():
    """Rapid taps from one user must be dropped, and the user told once."""
    import importlib

    from aiogram import Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage

    from handlers import common
    from middlewares import I18nMiddleware, ThrottlingMiddleware
    from tests.mocks import make_bot

    importlib.reload(common)
    bot, session = make_bot()

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ThrottlingMiddleware(rate=5))
    dp.message.middleware(I18nMiddleware())
    dp.include_router(common.router)

    for _ in range(4):
        await dp.feed_update(bot, message_update(USER_ID, "/help"))

    helps = [c for c in session.calls_of("SendMessage") if head(RU.HELP) in str(c.data.get("text", ""))]
    assert len(helps) == 1, "only the first message of a burst should be handled"
    assert session.said(RU.THROTTLED)


async def test_admins_are_not_throttled():
    """An admin uploading products must never be rate-limited mid-flow."""
    import importlib

    from aiogram import Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage

    from handlers import common
    from middlewares import I18nMiddleware, ThrottlingMiddleware
    from tests.mocks import make_bot

    importlib.reload(common)
    bot, session = make_bot()

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ThrottlingMiddleware(rate=5))
    dp.message.middleware(I18nMiddleware())
    dp.include_router(common.router)

    for _ in range(3):
        await dp.feed_update(bot, message_update(ADMIN_ID, "/help"))

    helps = [c for c in session.calls_of("SendMessage") if head(RU.HELP) in str(c.data.get("text", ""))]
    assert len(helps) == 3


# ---------------------------------------------------------------- commands

async def test_command_menu_covers_every_language():
    """A user on an Uzbek client should see Uzbek command descriptions."""
    import bot as bot_module

    for lang in LOCALES:
        commands = bot_module._commands(lang)
        names = [c.command for c in commands]
        assert names == ["start", "help", "language", "currency", "cancel"]
        assert all(c.description for c in commands)

    admin_commands = [c.command for c in bot_module._commands("ru", with_stats=True)]
    assert "stats" in admin_commands and "rates" in admin_commands
