"""Telegram Stars: pricing maths and the end-to-end payment flow."""
from __future__ import annotations

import pytest

from locales import get_texts
from tests.conftest import USER_ID
from tests.mocks import callback_update, contact_update, message_update
from tests.test_flow import build, feed, head
from utils.stars import MAX_STARS, MIN_STARS, stars_for

RU = get_texts("ru")
USD_RATE = 12101.84
STAR_PRICE = 0.02
SKIP_WORD = "нет"


# ---------------------------------------------------------------- pricing

def test_stars_for_a_realistic_order() -> None:
    # 11 500 000 so'm ≈ $950.27 ≈ 47 514 Stars at $0.02 each.
    assert stars_for(11_500_000, USD_RATE, STAR_PRICE) == 47_514


def test_stars_round_up() -> None:
    """Charging a fraction of a Star is impossible; rounding down sells at a loss."""
    # Exactly $0.021 -> 1.05 Stars -> 2.
    base = int(0.021 * USD_RATE)
    assert stars_for(base, USD_RATE, STAR_PRICE) == 2


def test_stars_never_below_one() -> None:
    assert stars_for(1, USD_RATE, STAR_PRICE) == MIN_STARS


def test_stars_are_capped() -> None:
    assert stars_for(10**15, USD_RATE, STAR_PRICE) == MAX_STARS


@pytest.mark.parametrize(
    ("base", "rate", "price"),
    [
        (0, USD_RATE, STAR_PRICE),        # nothing to charge
        (-100, USD_RATE, STAR_PRICE),     # negative total
        (1_000_000, None, STAR_PRICE),    # no USD rate
        (1_000_000, 0, STAR_PRICE),
        (1_000_000, -1, STAR_PRICE),
        (1_000_000, USD_RATE, 0),         # nonsensical Star price
        (1_000_000, USD_RATE, None),
    ],
)
def test_stars_refuses_to_guess(base, rate, price) -> None:
    """Without a defensible number, return None rather than invent one."""
    assert stars_for(base, rate, price) is None


# ---------------------------------------------------------------- flow

async def _place_order(dp, bot, db) -> int:
    await feed(dp, bot, message_update(USER_ID, "/start"))
    cat_id = (await db.get_categories("ru"))[0]["id"]
    prod = (await db.get_products(cat_id, "ru"))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{prod['id']}"))

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, contact_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))
    return (await db.get_user_orders(USER_ID))[0]["id"]


async def test_stars_button_is_offered_without_a_provider_token(clean_db):
    """The whole point: a demo can show payment with no merchant account."""
    from config import settings

    assert not settings.payment.enabled, "test env should have no provider token"

    db = clean_db
    bot, session, dp = await build()

    session.clear()
    await _place_order(dp, bot, db)

    buttons = []
    for call in session.calls:
        markup = call.data.get("reply_markup")
        if isinstance(markup, dict):
            for row in markup.get("inline_keyboard", []) or []:
                buttons += [b.get("text", "") for b in row]

    assert RU.BTN_PAY_STARS in buttons


async def test_stars_invoice_uses_xtr_and_no_provider_token(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await db.set_rate("USD", USD_RATE, source="api")
    from services.rates import rates

    rates.invalidate()

    order_id = await _place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:stars"))

    invoices = session.calls_of("SendInvoice")
    assert invoices, "a Stars invoice should have been sent"

    invoice = invoices[-1].data
    assert invoice["currency"] == "XTR"
    assert invoice.get("provider_token", "") == ""
    assert len(invoice["prices"]) == 1, "Stars allow exactly one price line"


async def test_demo_mode_charges_a_token_amount_and_says_so(clean_db):
    from config import settings

    db = clean_db
    bot, session, dp = await build()
    await db.set_rate("USD", USD_RATE, source="api")
    from services.rates import rates

    rates.invalidate()

    order_id = await _place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:stars"))

    invoice = session.calls_of("SendInvoice")[-1].data
    assert invoice["prices"][0]["amount"] == settings.payment.stars_demo_amount

    # The customer must be told this is a demo charge, not the real total.
    assert session.said(head(RU.PAY_STARS_DEMO_NOTICE))


async def test_stars_without_a_usd_rate_explains_itself(clean_db):
    """No rate means no defensible price — say so, do not invent one."""
    db = clean_db
    bot, session, dp = await build()
    order_id = await _place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:stars"))

    assert not session.calls_of("SendInvoice")
    assert session.said(head(RU.PAY_STARS_RATE_MISSING))


async def test_other_user_cannot_pay_with_stars(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await db.set_rate("USD", USD_RATE, source="api")
    from services.rates import rates

    rates.invalidate()

    order_id = await _place_order(dp, bot, db)

    intruder = 999
    await feed(dp, bot, message_update(intruder, "/start"))

    session.clear()
    await feed(dp, bot, callback_update(intruder, f"pay:{order_id}:stars"))

    assert not session.calls_of("SendInvoice")
    answers = session.calls_of("AnswerCallbackQuery")
    assert answers[-1].data.get("text") == RU.PAY_ORDER_NOT_FOUND


async def test_stars_pre_checkout_validates_the_amount(clean_db):
    """A tampered Stars amount must be refused, exactly like a card payment."""
    from config import settings

    from tests.mocks import pre_checkout_update

    db = clean_db
    bot, session, dp = await build()
    await db.set_rate("USD", USD_RATE, source="api")
    from services.rates import rates

    rates.invalidate()

    order_id = await _place_order(dp, bot, db)
    expected = settings.payment.stars_demo_amount

    session.clear()
    await feed(
        dp,
        bot,
        pre_checkout_update(USER_ID, f"order_{order_id}", expected + 100, "XTR"),
    )

    answers = session.calls_of("AnswerPreCheckoutQuery")
    assert answers and answers[-1].data.get("ok") is False


async def test_stars_pre_checkout_accepts_the_right_amount(clean_db):
    from config import settings

    from tests.mocks import pre_checkout_update

    db = clean_db
    bot, session, dp = await build()
    await db.set_rate("USD", USD_RATE, source="api")
    from services.rates import rates

    rates.invalidate()

    order_id = await _place_order(dp, bot, db)

    session.clear()
    await feed(
        dp,
        bot,
        pre_checkout_update(
            USER_ID,
            f"order_{order_id}",
            settings.payment.stars_demo_amount,
            "XTR",
        ),
    )

    answers = session.calls_of("AnswerPreCheckoutQuery")
    assert answers and answers[-1].data.get("ok") is True


async def test_paying_with_stars_marks_the_order_paid(clean_db):
    from config import settings

    from tests.mocks import payment_update

    db = clean_db
    bot, session, dp = await build()
    await db.set_rate("USD", USD_RATE, source="api")
    from services.rates import rates

    rates.invalidate()

    order_id = await _place_order(dp, bot, db)

    await feed(
        dp,
        bot,
        payment_update(
            USER_ID,
            f"order_{order_id}",
            settings.payment.stars_demo_amount,
            "STARS-CHARGE-1",
            "XTR",
        ),
    )

    order = await db.get_order(order_id)
    assert order["is_paid"] == 1
    assert order["status"] == "paid"
