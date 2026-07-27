"""Every payment method a customer in Uzbekistan or the CIS can pick."""
from __future__ import annotations

import pytest

from locales import get_texts
from payments import PROVIDERS, get_provider
from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import callback_update, contact_update, message_update
from tests.test_flow import build, feed, head
from tests.test_manual_gaps import photo_update

RU = get_texts("ru")
UZ = get_texts("uz")
SKIP_WORD = "нет"
USD_RATE = 12101.84


async def place_order(dp, bot, db) -> int:
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


def buttons_in(session) -> list[str]:
    out: list[str] = []
    for call in session.calls:
        markup = call.data.get("reply_markup")
        if isinstance(markup, dict):
            for row in markup.get("inline_keyboard", []) or []:
                out += [b.get("text", "") for b in row]
    return out


# ---------------------------------------------------------------- registry

def test_every_provider_has_a_label_in_every_locale() -> None:
    for code, provider in PROVIDERS.items():
        for lang in ("uz", "ru"):
            label = getattr(get_texts(lang), provider.label_key, None)
            assert label, f"{code} has no label in '{lang}'"


def test_manual_providers_ship_demo_requisites() -> None:
    """A fresh install must still show a filled-in transfer screen."""
    for code in ("card_uz", "sbp", "sber"):
        values = PROVIDERS[code].requisites()
        assert values and all(values), f"{code} has empty requisites"


def test_methods_needing_a_merchant_key_are_not_live_by_default() -> None:
    for code in ("payme", "click", "yoomoney"):
        assert not PROVIDERS[code].is_live


def test_methods_that_work_without_a_key_are_live() -> None:
    for code in ("card_uz", "sbp", "sber", "stars", "cash"):
        assert PROVIDERS[code].is_live


def test_unknown_provider_code_is_ignored() -> None:
    assert get_provider("paypal") is None
    assert get_provider(None) is None


# ---------------------------------------------------------------- the picker

async def test_all_methods_are_offered_after_an_order(clean_db):
    """The whole point: a client sees Payme, Click, СБП and the rest."""
    db = clean_db
    bot, session, dp = await build()

    session.clear()
    await place_order(dp, bot, db)
    labels = buttons_in(session)

    for expected in (
        RU.BTN_PAY_PAYME,
        RU.BTN_PAY_CLICK,
        RU.BTN_PAY_CARD_UZ,
        RU.BTN_PAY_SBP,
        RU.BTN_PAY_SBER,
        RU.BTN_PAY_YOOMONEY,
        RU.BTN_PAY_STARS,
        RU.BTN_PAY_CASH,
    ):
        assert expected in labels, f"missing payment button: {expected}"


async def test_methods_are_translated(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    session.clear()
    await place_order(dp, bot, db)
    labels = buttons_in(session)

    assert UZ.BTN_PAY_CARD_UZ in labels
    assert RU.BTN_PAY_CARD_UZ not in labels


async def test_payment_methods_can_be_narrowed(clean_db, monkeypatch):
    """A shop selling only inside Uzbekistan should not advertise СБП."""
    monkeypatch.setenv("PAYMENT_METHODS", "payme,click,card_uz,cash")

    db = clean_db
    bot, session, dp = await build()

    session.clear()
    await place_order(dp, bot, db)
    labels = buttons_in(session)

    assert RU.BTN_PAY_PAYME in labels
    assert RU.BTN_PAY_SBP not in labels
    assert RU.BTN_PAY_YOOMONEY not in labels


# ---------------------------------------------------------------- manual flow

async def test_manual_transfer_shows_requisites(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))

    said = " ".join(session.texts())
    card_number = PROVIDERS["card_uz"].requisites()[0]
    assert card_number in said, "the card number must be shown"
    assert str(order_id) in said
    assert RU.CURRENCY_SYMBOLS["UZS"] in said, "the amount must be shown"


async def test_sbp_shows_a_phone_not_a_card(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:sbp"))

    said = " ".join(session.texts())
    assert PROVIDERS["sbp"].requisites()[0] in said
    assert "📱" in said, "СБП is paid by phone number"


async def test_receipt_photo_creates_a_request_and_alerts_the_admin(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))

    session.clear()
    await feed(dp, bot, photo_update(USER_ID, "RECEIPT_PHOTO"))

    assert session.said(head(RU.PAY_RECEIPT_RECEIVED))

    photos = session.calls_of("SendPhoto")
    assert photos, "the admin must receive the receipt photo"
    assert photos[-1].data["photo"] == "RECEIPT_PHOTO"
    assert photos[-1].data.get("chat_id") == ADMIN_ID

    request = await db.get_payment_request(1)
    assert request and request["status"] == "pending"
    assert request["order_id"] == order_id
    assert request["method"] == "card_uz"


async def test_text_instead_of_a_receipt_is_rejected(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, "перевёл, честное слово"))

    assert session.said(head(RU.PAY_RECEIPT_NEED_PHOTO))
    assert await db.get_payment_request(1) is None


async def test_admin_approval_marks_the_order_paid(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))
    await feed(dp, bot, photo_update(USER_ID, "RECEIPT_PHOTO"))

    session.clear()
    await feed(dp, bot, callback_update(ADMIN_ID, "rcpt:1:True"))

    order = await db.get_order(order_id)
    assert order["is_paid"] == 1
    assert order["status"] == "paid"

    customer = [
        c for c in session.calls_of("SendMessage") if c.data.get("chat_id") == USER_ID
    ]
    assert customer, "the customer must be told"
    assert head(RU.PAY_RECEIPT_APPROVED) in str(customer[0].data.get("text", ""))


async def test_admin_rejection_leaves_the_order_unpaid(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))
    await feed(dp, bot, photo_update(USER_ID, "RECEIPT_PHOTO"))

    session.clear()
    await feed(dp, bot, callback_update(ADMIN_ID, "rcpt:1:False"))

    order = await db.get_order(order_id)
    assert order["is_paid"] == 0

    customer = [
        c for c in session.calls_of("SendMessage") if c.data.get("chat_id") == USER_ID
    ]
    assert customer
    assert head(RU.PAY_RECEIPT_REJECTED) in str(customer[0].data.get("text", ""))


async def test_a_receipt_cannot_be_reviewed_twice(clean_db):
    """Two admins tapping at once must not both succeed."""
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))
    await feed(dp, bot, photo_update(USER_ID, "RECEIPT_PHOTO"))

    await feed(dp, bot, callback_update(ADMIN_ID, "rcpt:1:True"))

    session.clear()
    await feed(dp, bot, callback_update(ADMIN_ID, "rcpt:1:False"))

    answers = session.calls_of("AnswerCallbackQuery")
    assert answers[-1].data.get("text") == RU.ADMIN_RECEIPT_ALREADY
    assert (await db.get_order(order_id))["is_paid"] == 1, "approval was undone"


async def test_a_customer_cannot_approve_their_own_receipt(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))
    await feed(dp, bot, photo_update(USER_ID, "RECEIPT_PHOTO"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "rcpt:1:True"))

    assert (await db.get_order(order_id))["is_paid"] == 0
    request = await db.get_payment_request(1)
    assert request["status"] == "pending"


async def test_receipt_for_someone_elses_order_is_refused(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)

    intruder = 999
    await feed(dp, bot, message_update(intruder, "/start"))

    session.clear()
    await feed(dp, bot, callback_update(intruder, f"pay:{order_id}:card_uz"))

    answers = session.calls_of("AnswerCallbackQuery")
    assert answers[-1].data.get("text") == RU.PAY_ORDER_NOT_FOUND


# ---------------------------------------------------------------- demo walkthrough

async def test_payme_without_a_key_explains_the_live_flow(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:payme"))

    said = " ".join(session.texts())
    assert RU.BTN_PAY_PAYME in said, "the method must be named"
    assert str(order_id) in said
    assert "демо" in said.lower(), "it must admit it is a demo"

    # And it must offer a route that actually works.
    assert RU.BTN_PAY_BY_RECEIPT in buttons_in(session)


async def test_the_demo_fallback_reaches_the_receipt_flow(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:payme"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))

    assert PROVIDERS["card_uz"].requisites()[0] in " ".join(session.texts())


async def test_a_configured_key_switches_payme_to_a_real_invoice(clean_db, monkeypatch):
    """The promise made on the demo screen has to hold."""
    monkeypatch.setenv("PAYME_TOKEN", "TEST:PAYME-TOKEN")

    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:payme"))

    invoices = session.calls_of("SendInvoice")
    assert invoices, "with a key configured a real invoice must be issued"
    assert invoices[-1].data["provider_token"] == "TEST:PAYME-TOKEN"
    assert invoices[-1].data["currency"] == "UZS"


async def test_yoomoney_without_a_key_falls_back_to_sbp(clean_db):
    """A Russian customer should be offered a Russian transfer, not an Uzbek card."""
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:yoomoney"))
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:sbp"))

    assert PROVIDERS["sbp"].requisites()[0] in " ".join(session.texts())


# ---------------------------------------------------------------- cash

async def test_cash_still_works(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:cash"))

    assert (await db.get_order(order_id))["status"] == "accepted"


async def test_a_paid_order_cannot_be_paid_again(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await place_order(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))
    await feed(dp, bot, photo_update(USER_ID, "RECEIPT_PHOTO"))
    await feed(dp, bot, callback_update(ADMIN_ID, "rcpt:1:True"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))

    answers = session.calls_of("AnswerCallbackQuery")
    assert answers[-1].data.get("text") == RU.PAY_ALREADY_PAID
