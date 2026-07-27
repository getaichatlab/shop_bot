"""End-to-end currency behaviour: switching, display, pinned prices, payment."""
from __future__ import annotations

import pytest

from currencies import BASE_CURRENCY
from locales import get_texts
from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import callback_update, contact_update, message_update
from tests.test_flow import build, feed, head
from tests.test_language_leak import collect_output

pytestmark = pytest.mark.asyncio

RU = get_texts("ru")
UZ = get_texts("uz")

USD_RATE = 12101.84
RUB_RATE = 153.75

SKIP_WORD = "нет"


async def seed_rates(db) -> None:
    await db.set_rate("USD", USD_RATE, source="api")
    await db.set_rate("RUB", RUB_RATE, source="api")
    from services.rates import rates

    rates.invalidate()


# ---------------------------------------------------------------- switching

async def test_default_currency_is_the_base_one(clean_db):
    db = clean_db
    bot, session, dp = await build()

    await feed(dp, bot, message_update(USER_ID, "/start"))
    assert await db.get_user_currency(USER_ID) == BASE_CURRENCY


async def test_currency_switch_is_stored(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/currency"))
    assert session.said(RU.CHOOSE_CURRENCY)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    assert await db.get_user_currency(USER_ID) == "USD"
    assert session.said(head(RU.CURRENCY_SET))


async def test_unknown_currency_is_ignored(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    await feed(dp, bot, callback_update(USER_ID, "cur:EUR"))
    assert await db.get_user_currency(USER_ID) == BASE_CURRENCY


async def test_currency_survives_restart(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    # New dispatcher, empty cache: the choice must come back from the database.
    bot2, session2, dp2 = await build()
    cat_id = (await db.get_categories("ru"))[0]["id"]
    await feed(dp2, bot2, callback_update(USER_ID, f"cat:{cat_id}"))

    assert "$" in collect_output(session2)


async def test_switching_currency_without_a_rate_warns(clean_db):
    """Silently showing base prices would look like a bug to the customer."""
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))
    assert session.said(head(RU.CURRENCY_RATE_MISSING))


# ---------------------------------------------------------------- display

async def test_catalog_prices_follow_the_currency(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))
    cat_id = (await db.get_categories("ru"))[0]["id"]

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"cat:{cat_id}"))
    assert RU.CURRENCY_SYMBOLS[BASE_CURRENCY] in collect_output(session)

    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))
    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"cat:{cat_id}"))
    output = collect_output(session)
    assert "$" in output
    assert RU.CURRENCY_SYMBOLS[BASE_CURRENCY] not in output


async def test_product_card_and_cart_use_the_currency(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:RUB"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"prd:{prod['id']}:{cat_id}"))
    assert "₽" in collect_output(session)

    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))
    session.clear()
    await feed(dp, bot, message_update(USER_ID, RU.BTN_CART))
    assert "₽" in collect_output(session)


async def test_cart_total_equals_the_sum_of_its_lines(clean_db):
    """The customer must be able to add the lines up and get the total."""
    from utils.money import cart_total_in, convert

    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    products = await db.get_products(cat_id, "ru")
    for product in products[:2]:
        await feed(dp, bot, callback_update(USER_ID, f"cadd:{product['id']}"))

    items = await db.cart_items(USER_ID, "ru", "USD")
    total = cart_total_in(items, "USD", USD_RATE)
    expected = sum(convert(i["price"], "USD", USD_RATE) * i["quantity"] for i in items)
    assert total == expected


async def test_price_without_a_rate_falls_back_to_base(clean_db):
    """No rate stored: prices stay in so'm rather than breaking the screen."""
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"cat:{cat_id}"))
    output = collect_output(session)

    assert RU.CURRENCY_SYMBOLS[BASE_CURRENCY] in output
    assert "$" not in output


# ---------------------------------------------------------------- pinned price

async def test_pinned_price_beats_the_rate(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await db.set_product_price(prod["id"], "USD", 9_900)   # exactly $99.00

    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"prd:{prod['id']}:{cat_id}"))
    assert "$99.00" in collect_output(session)


async def test_clearing_a_pinned_price_restores_conversion(clean_db):
    from utils.money import convert, format_amount

    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await db.set_product_price(prod["id"], "USD", 9_900)
    await db.clear_product_price(prod["id"], "USD")

    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"prd:{prod['id']}:{cat_id}"))

    converted = format_amount(convert(prod["price"], "USD", USD_RATE), "USD", RU)
    assert converted in collect_output(session)


async def test_pinned_price_is_per_currency(clean_db):
    """Pinning USD must not disturb what RUB shows."""
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await db.set_product_price(prod["id"], "USD", 9_900)

    rub = await db.get_product(prod["id"], "ru", "RUB")
    usd = await db.get_product(prod["id"], "ru", "USD")
    assert rub["price_override"] is None
    assert usd["price_override"] == 9_900


# ---------------------------------------------------------------- order

async def _checkout(dp, bot) -> None:
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, contact_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))


async def test_order_stores_base_total_and_display_snapshot(clean_db):
    """The base total drives payment; the snapshot preserves what was shown."""
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))

    await _checkout(dp, bot)

    order = (await db.get_user_orders(USER_ID))[0]
    assert order["total"] == prod["price"], "base total must stay in the base currency"
    assert order["display_currency"] == "USD"
    assert order["display_total"] and order["display_total"] != order["total"]


async def test_rate_change_does_not_rewrite_past_orders(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))
    await _checkout(dp, bot)

    before = (await db.get_user_orders(USER_ID))[0]["display_total"]

    await db.set_rate("USD", USD_RATE * 2, source="manual")
    from services.rates import rates

    rates.invalidate()

    after = (await db.get_user_orders(USER_ID))[0]["display_total"]
    assert before == after


async def test_admin_sees_orders_in_the_base_currency(clean_db):
    """A group chat has no user currency, so admin figures stay in the base one."""
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "cur:USD"))

    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))
    await _checkout(dp, bot)

    await feed(dp, bot, message_update(ADMIN_ID, "/start"))
    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_ORDERS))
    output = collect_output(session)

    assert RU.CURRENCY_SYMBOLS[BASE_CURRENCY] in output


# ---------------------------------------------------------------- admin rates

async def test_admin_can_see_the_rates_panel(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_RATES))
    output = collect_output(session)
    assert head(RU.ADMIN_RATES_HEADER) in output
    assert "USD" in output


async def test_non_admin_cannot_see_rates(clean_db):
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "/rates"))
    assert not session.said(head(RU.ADMIN_RATES_HEADER))


async def test_admin_can_set_a_rate_by_hand(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await seed_rates(db)
    await feed(dp, bot, message_update(ADMIN_ID, "/start"))

    await feed(dp, bot, callback_update(ADMIN_ID, "rate:edit:USD"))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "abc"))
    assert session.said(RU.ADMIN_RATE_INVALID)

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "-100"))
    assert session.said(RU.ADMIN_RATE_INVALID)

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, "13 000,50"))

    assert session.said(head(RU.ADMIN_RATE_SET))
    assert await db.get_rate("USD") == pytest.approx(13000.50)

    stored = await db.get_rates()
    assert stored["USD"]["source"] == "manual"
