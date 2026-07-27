"""Payments.

The bot offers the methods a customer in Uzbekistan or the CIS expects to see —
Payme, Click, a Humo/Uzcard transfer, СБП, a Сбербанк transfer, ЮMoney, Telegram
Stars and cash. `payments/providers.py` declares how each one collects money and
this module dispatches on that declaration.

Security rules applied (3.2.12 / 3.12):
  * invoice amounts are read from the database, never from the client;
  * pre-checkout re-validates the order, for Stars as well as for cards;
  * `record_payment` is idempotent — a retried callback cannot double-credit;
  * a receipt review is a conditional UPDATE, so two admins tapping at once
    cannot approve the same transfer twice.
"""
from __future__ import annotations

import logging
from types import ModuleType

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from config import settings
from currencies import BASE_CURRENCY
from database import db
from keyboards import inline
from locales import get_texts
from payments import (
    KIND_CASH,
    KIND_MANUAL,
    KIND_STARS,
    KIND_TELEGRAM,
    Provider,
    get_provider,
)
from services.rates import rates
from states import ReceiptState
from utils.callbacks import PayCB, ReceiptCB
from utils.formatters import esc, fmt_price
from utils.notifier import notify_admins, safe_edit, safe_send
from utils.stars import stars_for

router = Router(name="payment")
log = logging.getLogger(__name__)

PAYLOAD_PREFIX = "order_"

# Telegram Stars: empty provider token, currency XTR, exactly one price line.
STARS_CURRENCY = "XTR"

admin_texts = get_texts(settings.default_lang)


def _payload(order_id: int) -> str:
    return f"{PAYLOAD_PREFIX}{order_id}"


def _order_id_from_payload(payload: str) -> int | None:
    if not payload.startswith(PAYLOAD_PREFIX):
        return None
    raw = payload[len(PAYLOAD_PREFIX):]
    return int(raw) if raw.isdigit() else None


async def _load_order(call: CallbackQuery, order_id: int, t: ModuleType) -> dict | None:
    """Fetch the order, refusing anything that is not the caller's and unpaid."""
    order = await db.get_order(order_id)
    if not order or order["user_id"] != call.from_user.id:
        await call.answer(t.PAY_ORDER_NOT_FOUND, show_alert=True)
        return None
    if order["is_paid"]:
        await call.answer(t.PAY_ALREADY_PAID, show_alert=True)
        return None
    return order


# ----------------------------------------------------------------- dispatch

@router.callback_query(PayCB.filter())
async def choose_method(
    call: CallbackQuery, callback_data: PayCB, state: FSMContext, bot: Bot, t: ModuleType
) -> None:
    provider = get_provider(callback_data.method)
    if provider is None:
        await call.answer()
        return

    order = await _load_order(call, callback_data.order_id, t)
    if order is None:
        return

    if provider.kind == KIND_CASH:
        await _pay_cash(call, order, t)
    elif provider.kind == KIND_STARS:
        await _pay_stars(call, order, bot, t)
    elif provider.kind == KIND_MANUAL:
        await _pay_manual(call, order, provider, state, t)
    elif provider.kind == KIND_TELEGRAM:
        await _pay_telegram(call, order, provider, state, bot, t)

    await call.answer()


# ----------------------------------------------------------------- cash

async def _pay_cash(call: CallbackQuery, order: dict, t: ModuleType) -> None:
    await db.set_order_status(order["id"], "accepted")
    await safe_edit(call.message, t.PAY_CASH_DONE.format(order_id=order["id"]))


# ----------------------------------------------------------------- stars

async def _pay_stars(call: CallbackQuery, order: dict, bot: Bot, t: ModuleType) -> None:
    full_price = stars_for(
        order["total"], await rates.get("USD"), settings.payment.star_price_usd
    )
    if full_price is None:
        await call.message.answer(t.PAY_STARS_RATE_MISSING)
        return

    demo = settings.payment.is_demo
    charged = settings.payment.stars_demo_amount if demo else full_price
    total_text = fmt_price(order["total"], t)

    # Say plainly what is being charged. A demo that quietly bills a token
    # amount while showing the full price would be a lie on screen.
    notice = (
        t.PAY_STARS_DEMO_NOTICE.format(total=total_text, stars=charged)
        if demo
        else t.PAY_STARS_LIVE_NOTICE.format(total=total_text, stars=charged)
    )
    await call.message.answer(notice)

    title = t.PAY_STARS_TITLE.format(order_id=order["id"])
    try:
        await bot.send_invoice(
            chat_id=call.from_user.id,
            title=title,
            description=f"{order['name']} — {order['address']}"[:255],
            payload=_payload(order["id"]),
            provider_token="",
            currency=STARS_CURRENCY,
            prices=[LabeledPrice(label=title, amount=charged)],
        )
    except Exception as e:
        log.exception("Stars invoice failed for order %s: %s", order["id"], e)
        await call.message.answer(t.PAY_FAILED_PRECHECKOUT)


# ----------------------------------------------------------------- manual

def _render_requisites(provider: Provider, t: ModuleType) -> str:
    """Format the transfer details: account, holder, bank."""
    values = provider.requisites()
    if not values:
        return ""

    first_template = (
        t.PAY_MANUAL_REQUISITE_PHONE
        if provider.code == "sbp"
        else t.PAY_MANUAL_REQUISITE_CARD
    )
    templates = (
        first_template,
        t.PAY_MANUAL_REQUISITE_HOLDER,
        t.PAY_MANUAL_REQUISITE_BANK,
    )
    lines = [
        templates[index].format(value=esc(value))
        for index, value in enumerate(values)
        if value and index < len(templates)
    ]
    return "\n".join(lines)


async def _pay_manual(
    call: CallbackQuery,
    order: dict,
    provider: Provider,
    state: FSMContext,
    t: ModuleType,
) -> None:
    """Show the requisites and wait for a photo of the receipt."""
    await state.set_state(ReceiptState.photo)
    await state.update_data(order_id=order["id"], method=provider.code)

    text = t.PAY_MANUAL_INSTRUCTIONS.format(
        method=getattr(t, provider.label_key),
        amount=fmt_price(order["total"], t),
        order_id=order["id"],
        requisites=_render_requisites(provider, t),
    )
    # A publicly reachable demo shows card numbers. Say loudly that they are
    # not real, so nobody transfers money to a placeholder.
    if settings.payment.is_demo:
        text += t.PAY_MANUAL_DEMO_WARNING

    await call.message.answer(text)


# Telegram sends a picture as a `photo` when it is compressed, and as a
# `document` when the sender ticks "send as file" — which is exactly what
# happens with a screenshot dragged from a desktop. Both are receipts.
IMAGE_MIME_PREFIX = "image/"


def _receipt_file_id(message: Message) -> tuple[str, bool] | None:
    """Return (file_id, is_photo), or None if this is not an image."""
    if message.photo:
        # Largest size last — the readable one.
        return message.photo[-1].file_id, True
    document = message.document
    if document and (document.mime_type or "").startswith(IMAGE_MIME_PREFIX):
        return document.file_id, False
    return None


@router.message(ReceiptState.photo, F.photo | F.document)
async def receipt_received(
    message: Message, state: FSMContext, bot: Bot, t: ModuleType
) -> None:
    found = _receipt_file_id(message)
    if found is None:
        # A PDF, a voice note, a sticker — not something an admin can read.
        await message.answer(t.PAY_RECEIPT_NEED_IMAGE)
        return
    receipt_id, is_photo = found

    data = await state.get_data()
    order_id = data.get("order_id")
    method = data.get("method", "")
    await state.clear()

    order = await db.get_order(order_id) if order_id else None
    if not order or order["user_id"] != message.from_user.id:
        await message.answer(t.PAY_ORDER_NOT_FOUND)
        return
    if order["is_paid"]:
        await message.answer(t.PAY_ALREADY_PAID)
        return

    request_id = await db.create_payment_request(
        order_id=order["id"],
        user_id=message.from_user.id,
        method=method,
        receipt_id=receipt_id,
    )

    await message.answer(t.PAY_RECEIPT_RECEIVED.format(order_id=order["id"]))
    await _notify_admins_about_receipt(
        bot, request_id, order, method, receipt_id, is_photo
    )


@router.message(ReceiptState.photo)
async def receipt_wrong_type(message: Message, t: ModuleType) -> None:
    await message.answer(t.PAY_RECEIPT_NEED_PHOTO)


async def _notify_admins_about_receipt(
    bot: Bot,
    request_id: int,
    order: dict,
    method: str,
    receipt_id: str,
    is_photo: bool = True,
) -> None:
    a = admin_texts
    provider = get_provider(method)
    caption = a.ADMIN_RECEIPT_HEADER.format(
        order_id=order["id"],
        method=getattr(a, provider.label_key) if provider else esc(method),
        amount=fmt_price(order["total"], a),
        name=esc(order["name"]),
        phone=esc(order["phone"]),
    )
    markup = inline.receipt_review(request_id, a)

    targets = (
        [settings.bot.orders_chat_id]
        if settings.bot.orders_chat_id
        else settings.bot.admin_ids
    )
    for chat_id in targets:
        try:
            # A file_id keeps its type: a document cannot be re-sent as a photo.
            if is_photo:
                await bot.send_photo(
                    chat_id, receipt_id, caption=caption, reply_markup=markup
                )
            else:
                await bot.send_document(
                    chat_id, receipt_id, caption=caption, reply_markup=markup
                )
        except Exception as e:
            # The file may be unreachable; the admin still needs to know.
            log.warning("Receipt could not be delivered to %s: %s", chat_id, e)
            await safe_send(bot, chat_id, caption, markup)


@router.callback_query(ReceiptCB.filter())
async def review_receipt(
    call: CallbackQuery, callback_data: ReceiptCB, bot: Bot, t: ModuleType
) -> None:
    """Admin approves or rejects a transfer. Only admins reach this."""
    if call.from_user.id not in settings.bot.admin_ids:
        await call.answer(t.ADMIN_ONLY, show_alert=True)
        return

    request = await db.get_payment_request(callback_data.request_id)
    if not request:
        await call.answer(t.PAY_ORDER_NOT_FOUND, show_alert=True)
        return

    handled = await db.review_payment_request(
        callback_data.request_id, callback_data.approve
    )
    if not handled:
        await call.answer(t.ADMIN_RECEIPT_ALREADY, show_alert=True)
        return

    order_id = request["order_id"]
    template = (
        t.ADMIN_RECEIPT_APPROVED if callback_data.approve else t.ADMIN_RECEIPT_REJECTED
    )
    await call.answer(template.format(order_id=order_id))

    # Tell the customer, in their own language.
    customer_texts = get_texts(await db.get_user_language(request["user_id"]))
    message = (
        customer_texts.PAY_RECEIPT_APPROVED
        if callback_data.approve
        else customer_texts.PAY_RECEIPT_REJECTED
    ).format(order_id=order_id)

    delivered = await safe_send(bot, request["user_id"], message)
    if not delivered:
        await db.deactivate_user(request["user_id"])

    # Remove the buttons so the decision cannot be re-tapped.
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        log.debug("Could not clear the receipt keyboard")


# ----------------------------------------------------------------- telegram payments

async def _pay_telegram(
    call: CallbackQuery,
    order: dict,
    provider: Provider,
    state: FSMContext,
    bot: Bot,
    t: ModuleType,
) -> None:
    label = getattr(t, provider.label_key)

    if not provider.is_live:
        # No merchant key: walk the client through what the live flow looks like
        # and offer the transfer route, which does work today.
        await call.message.answer(
            t.PAY_DEMO_WALKTHROUGH.format(
                method=label,
                amount=fmt_price(order["total"], t),
                order_id=order["id"],
            ),
            reply_markup=inline.demo_fallback(order["id"], provider.region, t),
        )
        return

    # Payme and Click settle in the base currency only.
    if order["display_currency"] != BASE_CURRENCY:
        await call.message.answer(
            t.PAY_BASE_NOTICE.format(amount=fmt_price(order["total"], t)).strip()
        )

    try:
        await bot.send_invoice(
            chat_id=call.from_user.id,
            title=t.PAY_INVOICE_TITLE.format(order_id=order["id"]),
            description=f"{order['name']} — {order['address']}"[:255],
            payload=_payload(order["id"]),
            provider_token=provider.token,
            currency=settings.payment.currency,
            prices=[
                LabeledPrice(
                    label=t.PAY_INVOICE_TITLE.format(order_id=order["id"]),
                    amount=order["total"] * settings.payment.multiplier,
                )
            ],
        )
    except Exception as e:
        log.exception("send_invoice failed for order %s: %s", order["id"], e)
        await call.message.answer(t.PAY_FAILED_PRECHECKOUT)


# ----------------------------------------------------------------- checkout

async def _expected_stars(order: dict) -> int | None:
    """What a Stars invoice for this order should charge, recomputed server-side."""
    if settings.payment.is_demo:
        return settings.payment.stars_demo_amount
    return stars_for(
        order["total"], await rates.get("USD"), settings.payment.star_price_usd
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot, t: ModuleType) -> None:
    """Re-validate server-side before letting the charge go through."""
    order_id = _order_id_from_payload(query.invoice_payload or "")
    if order_id is None:
        await bot.answer_pre_checkout_query(
            query.id, ok=False, error_message=t.PAY_ORDER_NOT_FOUND
        )
        return

    order = await db.get_order(order_id)
    if not order or order["user_id"] != query.from_user.id:
        await bot.answer_pre_checkout_query(
            query.id, ok=False, error_message=t.PAY_ORDER_NOT_FOUND
        )
        return
    if order["is_paid"]:
        await bot.answer_pre_checkout_query(
            query.id, ok=False, error_message=t.PAY_ALREADY_PAID
        )
        return

    if query.currency == STARS_CURRENCY:
        expected = await _expected_stars(order)
    else:
        expected = order["total"] * settings.payment.multiplier

    if expected is None or query.total_amount != expected:
        log.error(
            "Amount mismatch for order %s in %s: got %s, expected %s",
            order_id, query.currency, query.total_amount, expected,
        )
        await bot.answer_pre_checkout_query(
            query.id, ok=False, error_message=t.PAY_FAILED_PRECHECKOUT
        )
        return

    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def payment_success(message: Message, bot: Bot, t: ModuleType) -> None:
    payment = message.successful_payment
    order_id = _order_id_from_payload(payment.invoice_payload or "")
    if order_id is None:
        log.error("Unknown payment payload: %s", payment.invoice_payload)
        return

    is_new = await db.record_payment(
        order_id=order_id,
        user_id=message.from_user.id,
        amount=payment.total_amount,
        currency=payment.currency,
        charge_id=payment.telegram_payment_charge_id,
        provider_charge_id=payment.provider_payment_charge_id,
    )

    await message.answer(t.PAY_SUCCESS.format(order_id=order_id))

    if is_new:
        await notify_admins(
            bot, admin_texts.ADMIN_PAID_NOTICE.format(order_id=esc(order_id))
        )
