"""End-to-end handler tests against a fake Telegram transport.

Real dispatcher, real routers, real middlewares, real FSM, real database —
only the network call is mocked.

Assertions read their expected strings from the locale modules, so translating
the bot never breaks the test suite. Run: pytest -q
"""
from __future__ import annotations

import pytest

from locales import get_texts
from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import (
    callback_update,
    contact_update,
    make_bot,
    message_update,
    payment_update,
    pre_checkout_update,
)

pytestmark = pytest.mark.asyncio

RU = get_texts("ru")
UZ = get_texts("uz")

# The bot's default language in tests (see conftest DEFAULT_LANG).
T = RU
SKIP_WORD = "нет"


async def build():
    """Fresh bot + dispatcher for one test.

    Routers are module-level singletons and aiogram refuses to re-attach a
    router that already has a parent, so the handler modules are reloaded to
    produce brand-new Router objects for every test.
    """
    import importlib

    from aiogram import Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage

    from handlers import admin, cart, catalog, common, errors, order, payment
    from middlewares import ActivityMiddleware, I18nMiddleware, ThrottlingMiddleware

    modules = [common, catalog, cart, order, payment, admin, errors]
    for module in modules:
        importlib.reload(module)

    bot, session = make_bot()

    dp = Dispatcher(storage=MemoryStorage())
    i18n = I18nMiddleware()
    for observer in (dp.message, dp.callback_query):
        observer.middleware(ThrottlingMiddleware(rate=0))
        observer.middleware(i18n)
        observer.middleware(ActivityMiddleware())
    dp.pre_checkout_query.middleware(i18n)

    for module in modules:
        dp.include_router(module.router)

    return bot, session, dp


async def feed(dp, bot, update):
    return await dp.feed_update(bot, update)


def head(template: str, words: int = 2) -> str:
    """First few words of a template, before any placeholder."""
    return template.split("{")[0].strip()[:40]


# ---------------------------------------------------------------- start

async def test_start_creates_user_once(clean_db):
    db = clean_db
    bot, session, dp = await build()

    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, message_update(USER_ID, "/start"))

    assert session.said(head(T.WELCOME))
    assert await db.get_active_user_ids() == [USER_ID]


async def test_new_user_gets_default_language(clean_db):
    db = clean_db
    bot, session, dp = await build()

    await feed(dp, bot, message_update(USER_ID, "/start"))
    assert await db.get_user_language(USER_ID) == "ru"


async def test_help_and_cancel_without_state(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/help"))
    assert session.said(head(T.HELP))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/cancel"))
    assert session.said(T.NOTHING_TO_CANCEL)


# ---------------------------------------------------------------- language

async def test_language_switch_changes_interface(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/language"))
    assert session.said(T.CHOOSE_LANGUAGE)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    assert await db.get_user_language(USER_ID) == "uz"
    assert session.said(UZ.LANGUAGE_SET)

    # The interface now answers in Uzbek.
    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/help"))
    assert session.said(head(UZ.HELP))


async def test_uzbek_buttons_work_after_switch(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, UZ.BTN_CATALOG))
    assert session.said(UZ.CHOOSE_CATEGORY)


async def test_russian_buttons_still_work_for_uzbek_user(clean_db):
    """A stale keyboard from the previous language must not dead-end the user."""
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, RU.BTN_CATALOG))
    assert session.said(UZ.CHOOSE_CATEGORY)


async def test_language_survives_restart(clean_db):
    """The choice is stored in the database, not only in the in-memory cache."""
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    # A brand-new dispatcher means a brand-new (empty) i18n cache.
    bot2, session2, dp2 = await build()
    await feed(dp2, bot2, message_update(USER_ID, "/help"))
    assert session2.said(head(UZ.HELP))


async def test_start_does_not_reset_chosen_language(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    await feed(dp, bot, message_update(USER_ID, "/start"))
    assert await db.get_user_language(USER_ID) == "uz"


async def test_unknown_language_code_is_ignored(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    await feed(dp, bot, callback_update(USER_ID, "lng:de"))
    assert await db.get_user_language(USER_ID) == "ru"


# ---------------------------------------------------------------- catalog

async def test_catalog_browsing(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, T.BTN_CATALOG))
    assert session.said(T.CHOOSE_CATEGORY)

    cat_id = (await db.get_categories())[0]["id"]

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"cat:{cat_id}"))
    assert session.said(T.CHOOSE_PRODUCT)

    prod = (await db.get_products(cat_id))[0]

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"prd:{prod['id']}:{cat_id}"))
    assert session.said(prod["title"])


async def test_unknown_product_is_rejected(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "cadd:999999"))

    answers = session.calls_of("AnswerCallbackQuery")
    assert answers, "callback must be answered"
    assert answers[-1].data.get("text") == T.PRODUCT_NOT_FOUND


# ---------------------------------------------------------------- cart

async def test_cart_add_and_quantity(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    cat_id = (await db.get_categories())[0]["id"]
    prod = (await db.get_products(cat_id))[0]

    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))
    assert await db.cart_total(USER_ID) == prod["price"]

    await feed(dp, bot, callback_update(USER_ID, f"cqty:{prod['id']}:1"))
    assert await db.cart_total(USER_ID) == prod["price"] * 2

    await feed(dp, bot, callback_update(USER_ID, f"cqty:{prod['id']}:-1"))
    assert await db.cart_total(USER_ID) == prod["price"]

    # Decreasing below 1 removes the line entirely.
    await feed(dp, bot, callback_update(USER_ID, f"cqty:{prod['id']}:-1"))
    assert await db.cart_items(USER_ID) == []


async def test_empty_cart_message(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, T.BTN_CART))
    assert session.said(head(T.CART_EMPTY))


# ---------------------------------------------------------------- checkout

async def _fill_cart(dp, bot, db) -> int:
    cat_id = (await db.get_categories())[0]["id"]
    prod = (await db.get_products(cat_id))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))
    return prod["price"]


async def test_full_checkout_flow(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    price = await _fill_cart(dp, bot, db)

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "Ab"))
    assert session.said(T.ERR_NAME_SHORT)

    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "abc"))
    assert session.said(head(T.ERR_PHONE_INVALID))

    await feed(dp, bot, contact_update(USER_ID, "+998901234567"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "abc"))
    assert session.said(T.ERR_ADDRESS_SHORT)

    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12, 45-xonadon"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    assert session.said(head(T.ORDER_CONFIRM_HEADER))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))
    assert session.said(head(T.ORDER_ACCEPTED))

    orders = await db.get_user_orders(USER_ID)
    assert len(orders) == 1
    assert orders[0]["total"] == price
    assert orders[0]["name"] == "Tolibjon Boydullayev"
    assert orders[0]["phone"] == "+998901234567"
    assert orders[0]["comment"] == "", "skip word must store an empty comment"
    assert await db.cart_items(USER_ID) == [], "cart must be emptied"


async def test_checkout_in_uzbek(clean_db):
    """The whole flow must work end to end in the second language too."""
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))
    await _fill_cart(dp, bot, db)

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "Ab"))
    assert session.said(UZ.ERR_NAME_SHORT)

    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, message_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "yo'q"))
    assert session.said(head(UZ.ORDER_CONFIRM_HEADER))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))
    assert session.said(head(UZ.ORDER_ACCEPTED))
    assert len(await db.get_user_orders(USER_ID)) == 1


async def test_checkout_cancel_keeps_cart(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await _fill_cart(dp, bot, db)

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, T.BTN_CANCEL))

    assert session.said(T.CANCELLED)
    assert await db.cart_items(USER_ID) != [], "cancelling must not clear the cart"
    assert await db.get_user_orders(USER_ID) == []


async def test_admin_is_notified_about_new_order(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await _fill_cart(dp, bot, db)

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, message_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))

    admin_messages = [
        c for c in session.calls_of("SendMessage") if c.data.get("chat_id") == ADMIN_ID
    ]
    assert admin_messages, "admin must receive the new order"
    assert head(T.ADMIN_NEW_ORDER_HEADER) in str(admin_messages[0].data.get("text", ""))


# ---------------------------------------------------------------- payment

async def _place_order(dp, bot, db) -> int:
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await _fill_cart(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, message_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))
    return (await db.get_user_orders(USER_ID))[0]["id"]


async def test_cash_payment_sets_accepted(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await _place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:cash"))

    assert (await db.get_order(order_id))["status"] == "accepted"


async def test_other_user_cannot_pay_someone_elses_order(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await _place_order(dp, bot, db)

    intruder = 999
    await feed(dp, bot, message_update(intruder, "/start"))

    session.clear()
    await feed(dp, bot, callback_update(intruder, f"pay:{order_id}:cash"))

    answers = session.calls_of("AnswerCallbackQuery")
    assert answers[-1].data.get("text") == T.PAY_ORDER_NOT_FOUND
    assert (await db.get_order(order_id))["status"] == "new"


async def test_successful_payment_is_idempotent(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await _place_order(dp, bot, db)
    total = (await db.get_order(order_id))["total"]

    await feed(
        dp, bot, payment_update(USER_ID, f"order_{order_id}", total * 100, "CHARGE-X")
    )
    assert (await db.get_order(order_id))["is_paid"] == 1

    session.clear()
    # Same charge id delivered twice (Telegram retry).
    await feed(
        dp, bot, payment_update(USER_ID, f"order_{order_id}", total * 100, "CHARGE-X")
    )
    admin_notices = [
        c
        for c in session.calls_of("SendMessage")
        if c.data.get("chat_id") == ADMIN_ID
        and head(T.ADMIN_PAID_NOTICE) in str(c.data.get("text", ""))
    ]
    assert not admin_notices, "duplicate payment must not notify twice"


async def test_pre_checkout_rejects_wrong_amount(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await _place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, pre_checkout_update(USER_ID, f"order_{order_id}", 100))

    answers = session.calls_of("AnswerPreCheckoutQuery")
    assert answers and answers[-1].data.get("ok") is False


async def test_pre_checkout_accepts_correct_amount(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await _place_order(dp, bot, db)
    total = (await db.get_order(order_id))["total"]

    session.clear()
    await feed(dp, bot, pre_checkout_update(USER_ID, f"order_{order_id}", total * 100))

    answers = session.calls_of("AnswerPreCheckoutQuery")
    assert answers and answers[-1].data.get("ok") is True


# ---------------------------------------------------------------- admin

async def test_non_admin_cannot_open_panel(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, T.BTN_ADMIN))
    assert not session.said(T.ADMIN_PANEL)


async def test_admin_panel_and_stats(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, T.BTN_ADMIN))
    assert session.said(T.ADMIN_PANEL)

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "/stats"))
    assert session.said(head(T.ADMIN_STATS))


async def test_non_admin_stats_command_is_ignored(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/stats"))
    assert not session.said(head(T.ADMIN_STATS))


async def test_admin_adds_category_in_every_language(clean_db):
    """Catalog text is business data: the admin supplies it once per language."""
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))
    await feed(dp, bot, message_update(ADMIN_ID, T.BTN_ADD_CATEGORY))

    # LANGUAGE_ORDER is ("ru", "uz"), so Russian is asked first.
    await feed(dp, bot, message_update(ADMIN_ID, "Планшеты"))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "Planshetlar"))
    assert session.said(head(T.ADMIN_CATEGORY_ADDED))

    ru_titles = [c["title"] for c in await db.get_categories("ru")]
    uz_titles = [c["title"] for c in await db.get_categories("uz")]
    assert "Планшеты" in ru_titles and "Planshetlar" not in ru_titles
    assert "Planshetlar" in uz_titles and "Планшеты" not in uz_titles


async def test_admin_category_asks_for_the_second_language(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))
    await feed(dp, bot, message_update(ADMIN_ID, T.BTN_ADD_CATEGORY))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "Планшеты"))

    # It must now ask for the Uzbek name, not save straight away.
    assert session.said(UZ.LANG_NAME)
    assert not session.said(head(T.ADMIN_CATEGORY_ADDED))


async def test_admin_status_change_notifies_customer_in_their_language(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await _place_order(dp, bot, db)

    # The customer switches to Uzbek after ordering.
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    session.clear()
    await feed(dp, bot, callback_update(ADMIN_ID, f"ast:{order_id}:shipping"))

    assert (await db.get_order(order_id))["status"] == "shipping"
    customer_messages = [
        c for c in session.calls_of("SendMessage") if c.data.get("chat_id") == USER_ID
    ]
    assert customer_messages
    text = str(customer_messages[0].data.get("text", ""))
    assert head(UZ.ORDER_STATUS_CHANGED) in text
    assert UZ.STATUS_LABELS["shipping"] in text


async def test_admin_adds_product_with_price_validation(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))
    await feed(dp, bot, message_update(ADMIN_ID, T.BTN_ADD_PRODUCT))

    cat_id = (await db.get_categories())[0]["id"]
    await feed(dp, bot, callback_update(ADMIN_ID, f"acat:{cat_id}"))

    # Title, then description, each once per language (ru first, then uz).
    await feed(dp, bot, message_update(ADMIN_ID, "Тестовый товар"))
    await feed(dp, bot, message_update(ADMIN_ID, "Test mahsulot"))
    await feed(dp, bot, message_update(ADMIN_ID, "Описание"))
    await feed(dp, bot, message_update(ADMIN_ID, "Tavsif"))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "-500"))
    assert session.said(head(T.ERR_PRICE_INVALID))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "abc"))
    assert session.said(head(T.ERR_PRICE_INVALID))

    await feed(dp, bot, message_update(ADMIN_ID, "1 250 000"))

    # One prompt per extra currency: an exact price for RUB, automatic for USD.
    await feed(dp, bot, message_update(ADMIN_ID, "8 000"))
    await feed(dp, bot, message_update(ADMIN_ID, T.BTN_PRICE_AUTO))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, SKIP_WORD))

    assert session.said(head(T.ADMIN_PRODUCT_ADDED))

    ru_products = {p["title"]: p for p in await db.get_products(cat_id, "ru")}
    uz_products = {p["title"]: p for p in await db.get_products(cat_id, "uz")}
    assert "Тестовый товар" in ru_products
    assert "Test mahsulot" in uz_products
    assert ru_products["Тестовый товар"]["price"] == 1_250_000
    assert ru_products["Тестовый товар"]["description"] == "Описание"
    assert uz_products["Test mahsulot"]["description"] == "Tavsif"

    # The RUB price was pinned; USD was left to the exchange rate.
    product_id = ru_products["Тестовый товар"]["id"]
    pinned = await db.get_product_prices(product_id)
    assert pinned == {"RUB": 8_000}


# ---------------------------------------------------------------- safety

async def test_html_injection_is_escaped(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await _fill_cart(dp, bot, db)

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "<b>Hacker</b> Name"))
    await feed(dp, bot, message_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))

    joined = " ".join(session.texts())
    assert "&lt;b&gt;Hacker&lt;/b&gt;" in joined
    assert "<b>Hacker</b>" not in joined
