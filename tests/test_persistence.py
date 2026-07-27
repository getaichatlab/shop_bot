"""What must survive: the cart across a restart, the profile across orders,
and a receipt sent as a file rather than a compressed photo.
"""
from __future__ import annotations

from datetime import datetime, timezone

from aiogram.types import Chat, Document, Message, Update

from locales import get_texts
from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import (
    _next_msg_id,
    _next_update_id,
    callback_update,
    contact_update,
    make_user,
    message_update,
)
from tests.test_flow import build, feed, head

RU = get_texts("ru")
SKIP_WORD = "нет"


def document_update(user_id: int, file_id: str, mime: str = "image/png") -> Update:
    """A picture sent with 'send as file' — Telegram delivers a document."""
    return Update(
        update_id=_next_update_id(),
        message=Message(
            message_id=_next_msg_id(),
            date=datetime.now(timezone.utc),
            chat=Chat(id=user_id, type="private"),
            from_user=make_user(user_id),
            document=Document(
                file_id=file_id,
                file_unique_id="u-doc",
                file_name="receipt.png",
                mime_type=mime,
                file_size=143_700,
            ),
        ),
    )


async def add_to_cart(dp, bot, db, index: int = 0) -> dict:
    cat_id = (await db.get_categories("ru"))[0]["id"]
    product = (await db.get_products(cat_id, "ru"))[index]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{product['id']}"))
    return product


# ---------------------------------------------------------------- cart

async def test_cart_survives_a_restart(clean_db):
    """The cart lives in the database, not in memory."""
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    product = await add_to_cart(dp, bot, db)

    before = await db.cart_items(USER_ID, "ru", "UZS")
    assert len(before) == 1

    # A brand-new dispatcher and bot: everything in memory is gone.
    bot2, session2, dp2 = await build()

    after = await db.cart_items(USER_ID, "ru", "UZS")
    assert after == before, "the cart was lost on restart"

    session2.clear()
    await feed(dp2, bot2, message_update(USER_ID, RU.BTN_CART))
    assert session2.said(product["title"])


async def test_quantities_survive_a_restart(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    product = await add_to_cart(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, f"cqty:{product['id']}:1"))
    await feed(dp, bot, callback_update(USER_ID, f"cqty:{product['id']}:1"))

    bot2, session2, dp2 = await build()
    items = await db.cart_items(USER_ID, "ru", "UZS")
    assert items[0]["quantity"] == 3


async def test_carts_do_not_leak_between_users(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await add_to_cart(dp, bot, db)

    other = 12345
    await feed(dp, bot, message_update(other, "/start"))

    assert await db.cart_items(other, "ru", "UZS") == []
    assert len(await db.cart_items(USER_ID, "ru", "UZS")) == 1


# ---------------------------------------------------------------- profile

async def _first_order(dp, bot, db) -> None:
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await add_to_cart(dp, bot, db)
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, contact_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))


async def test_profile_is_saved_after_the_first_order(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await _first_order(dp, bot, db)

    profile = await db.get_profile(USER_ID)
    assert profile == {"name": "Tolibjon Boydullayev", "phone": "+998901234567"}


async def test_second_order_does_not_ask_for_name_or_phone(clean_db):
    """The whole point: a returning customer goes straight to the address."""
    db = clean_db
    bot, session, dp = await build()
    await _first_order(dp, bot, db)

    await add_to_cart(dp, bot, db, index=1)
    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))

    said = " ".join(session.texts())
    assert head(RU.ORDER_STEP_NAME) not in said, "the name was asked again"
    assert head(RU.ORDER_STEP_PHONE) not in said, "the phone was asked again"
    assert "+998901234567" in said, "the saved phone should be shown"
    assert head(RU.ORDER_PROFILE_SAVED) in said


async def test_second_order_completes_from_the_address_step(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await _first_order(dp, bot, db)

    await add_to_cart(dp, bot, db, index=1)
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Chilonzor 5"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))

    orders = await db.get_user_orders(USER_ID)
    assert len(orders) == 2
    latest = orders[0]
    assert latest["name"] == "Tolibjon Boydullayev"
    assert latest["phone"] == "+998901234567"
    assert latest["address"] == "Toshkent, Chilonzor 5", "the new address must be used"


async def test_profile_survives_a_restart(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await _first_order(dp, bot, db)

    bot2, session2, dp2 = await build()
    await add_to_cart(dp2, bot2, db, index=1)

    session2.clear()
    await feed(dp2, bot2, callback_update(USER_ID, "nav:checkout"))
    assert "+998901234567" in " ".join(session2.texts())


async def test_the_customer_can_change_their_details(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await _first_order(dp, bot, db)

    await add_to_cart(dp, bot, db, index=1)
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))

    session.clear()
    await feed(dp, bot, message_update(USER_ID, RU.BTN_EDIT_PROFILE))

    assert session.said(RU.PROFILE_CLEARED)
    assert session.said(head(RU.ORDER_STEP_NAME))
    assert await db.get_profile(USER_ID) is None

    # And the new details are used and remembered.
    await feed(dp, bot, message_update(USER_ID, "Bekzod Karimov"))
    await feed(dp, bot, message_update(USER_ID, "+998905554433"))
    await feed(dp, bot, message_update(USER_ID, "Samarqand, Registon 1"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))

    assert await db.get_profile(USER_ID) == {
        "name": "Bekzod Karimov",
        "phone": "+998905554433",
    }


async def test_a_failed_order_does_not_save_the_profile(clean_db):
    """Cancelling halfway must not leave half a profile behind."""
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await add_to_cart(dp, bot, db)

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
    await feed(dp, bot, message_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, RU.BTN_CANCEL))

    assert await db.get_profile(USER_ID) is None


async def test_profiles_are_per_user(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await _first_order(dp, bot, db)

    other = 12345
    await feed(dp, bot, message_update(other, "/start"))
    assert await db.get_profile(other) is None


# ---------------------------------------------------------------- receipts

async def _reach_receipt_step(dp, bot, db) -> int:
    await _first_order(dp, bot, db)
    order_id = (await db.get_user_orders(USER_ID))[0]["id"]
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))
    return order_id


async def test_a_receipt_sent_as_a_file_is_accepted(clean_db):
    """Dragging a screenshot from a desktop sends a document, not a photo."""
    db = clean_db
    bot, session, dp = await build()
    order_id = await _reach_receipt_step(dp, bot, db)

    session.clear()
    await feed(dp, bot, document_update(USER_ID, "RECEIPT_AS_FILE"))

    assert session.said(head(RU.PAY_RECEIPT_RECEIVED))

    request = await db.get_payment_request(1)
    assert request and request["receipt_id"] == "RECEIPT_AS_FILE"
    assert request["order_id"] == order_id


async def test_a_file_receipt_reaches_the_admin_as_a_document(clean_db):
    """A document file_id cannot be re-sent as a photo — Telegram refuses."""
    db = clean_db
    bot, session, dp = await build()
    await _reach_receipt_step(dp, bot, db)

    session.clear()
    await feed(dp, bot, document_update(USER_ID, "RECEIPT_AS_FILE"))

    documents = session.calls_of("SendDocument")
    assert documents, "the admin should receive it as a document"
    assert documents[-1].data["document"] == "RECEIPT_AS_FILE"
    assert documents[-1].data.get("chat_id") == ADMIN_ID
    assert not session.calls_of("SendPhoto")


async def test_a_pdf_receipt_is_refused(clean_db):
    """A PDF is not something the admin can glance at in the chat."""
    db = clean_db
    bot, session, dp = await build()
    await _reach_receipt_step(dp, bot, db)

    session.clear()
    await feed(dp, bot, document_update(USER_ID, "RECEIPT.pdf", "application/pdf"))

    assert session.said(head(RU.PAY_RECEIPT_NEED_IMAGE))
    assert await db.get_payment_request(1) is None


async def test_a_file_receipt_can_be_approved(clean_db):
    db = clean_db
    bot, session, dp = await build()
    order_id = await _reach_receipt_step(dp, bot, db)
    await feed(dp, bot, document_update(USER_ID, "RECEIPT_AS_FILE"))

    await feed(dp, bot, callback_update(ADMIN_ID, "rcpt:1:True"))

    order = await db.get_order(order_id)
    assert order["is_paid"] == 1
