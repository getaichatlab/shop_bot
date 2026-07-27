"""Checkout flow (FSM) and order history."""
from __future__ import annotations

import logging
from types import ModuleType

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import settings
from currencies import BASE_CURRENCY
from database import db
from filters import Btn, is_admin
from keyboards import inline, reply
from locales import get_texts
from states import OrderState
from utils import validators
from utils.callbacks import NavAction, NavCB, OrderAction, OrderCB
from services.rates import rates
from utils.formatters import esc, fmt_dt, fmt_price
from utils.money import cart_total_in, format_amount
from utils.notifier import notify_admins, safe_edit

router = Router(name="order")
log = logging.getLogger(__name__)

# Admin-facing notifications always use the bot's default language, because a
# group chat has no single user language.
admin_texts = get_texts(settings.default_lang)


# ----------------------------------------------------------------- entry

@router.callback_query(NavCB.filter(F.action == NavAction.checkout))
async def checkout_start(
    call: CallbackQuery, state: FSMContext, t: ModuleType, lang: str, currency: str
) -> None:
    items = await db.cart_items(call.from_user.id, lang, currency)
    if not items:
        await call.answer(t.CART_EMPTY, show_alert=True)
        return

    # A publicly reachable bot will be poked at. Cap how many unfinished orders
    # one account can pile up, so the database cannot be filled by clicking.
    open_orders = await db.count_open_orders(call.from_user.id)
    if open_orders >= settings.max_open_orders:
        await call.answer(
            t.ORDER_TOO_MANY_OPEN.format(count=open_orders), show_alert=True
        )
        return

    # Name and phone are asked once and reused. Making a returning customer
    # retype their phone on every order is the fastest way to lose the sale.
    profile = await db.get_profile(call.from_user.id)
    if profile:
        await state.update_data(name=profile["name"], phone=profile["phone"])
        await state.set_state(OrderState.address)
        await call.message.answer(
            t.ORDER_PROFILE_SAVED.format(
                name=esc(profile["name"]), phone=esc(profile["phone"])
            ),
            reply_markup=reply.address_with_edit(t),
        )
        await call.answer()
        return

    await state.set_state(OrderState.name)
    await call.message.answer(t.ORDER_STEP_NAME, reply_markup=reply.cancel_only(t))
    await call.answer()


# ----------------------------------------------------------------- steps

@router.message(Btn("BTN_EDIT_PROFILE"))
async def edit_profile(message: Message, state: FSMContext, t: ModuleType) -> None:
    """Forget the saved name and phone and ask for them again."""
    await db.clear_profile(message.from_user.id)
    await state.set_state(OrderState.name)
    await state.update_data(name=None, phone=None)
    await message.answer(t.PROFILE_CLEARED)
    await message.answer(t.ORDER_STEP_NAME, reply_markup=reply.cancel_only(t))


@router.message(OrderState.name, F.text)
async def step_name(message: Message, state: FSMContext, t: ModuleType) -> None:
    ok, result = validators.validate_name(message.text)
    if not ok:
        if result == "short":
            await message.answer(t.ERR_NAME_SHORT)
        else:
            await message.answer(t.ERR_NAME_LONG.format(limit=validators.NAME_MAX))
        return
    await state.update_data(name=result)
    await state.set_state(OrderState.phone)
    await message.answer(t.ORDER_STEP_PHONE, reply_markup=reply.phone_request(t))


@router.message(OrderState.name)
async def step_name_wrong_type(message: Message, t: ModuleType) -> None:
    await message.answer(t.ERR_TEXT_EXPECTED)


@router.message(OrderState.phone, F.contact)
async def step_phone_contact(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    await state.update_data(
        phone=validators.normalize_phone(message.contact.phone_number)
    )
    await _ask_address(message, state, t)


@router.message(OrderState.phone, F.text)
async def step_phone_text(message: Message, state: FSMContext, t: ModuleType) -> None:
    if not validators.is_valid_phone(message.text):
        await message.answer(t.ERR_PHONE_INVALID)
        return
    await state.update_data(phone=validators.normalize_phone(message.text))
    await _ask_address(message, state, t)


@router.message(OrderState.phone)
async def step_phone_wrong_type(message: Message, t: ModuleType) -> None:
    await message.answer(t.ERR_TEXT_EXPECTED)


async def _ask_address(message: Message, state: FSMContext, t: ModuleType) -> None:
    await state.set_state(OrderState.address)
    await message.answer(t.ORDER_STEP_ADDRESS, reply_markup=reply.cancel_only(t))


@router.message(OrderState.address, F.text)
async def step_address(message: Message, state: FSMContext, t: ModuleType) -> None:
    ok, result = validators.validate_address(message.text)
    if not ok:
        if result == "short":
            await message.answer(t.ERR_ADDRESS_SHORT)
        else:
            await message.answer(
                t.ERR_ADDRESS_LONG.format(limit=validators.ADDRESS_MAX)
            )
        return
    await state.update_data(address=result)
    await state.set_state(OrderState.comment)
    await message.answer(t.ORDER_STEP_COMMENT)


@router.message(OrderState.address)
async def step_address_wrong_type(message: Message, t: ModuleType) -> None:
    await message.answer(t.ERR_TEXT_EXPECTED)


@router.message(OrderState.comment, F.text)
async def step_comment(
    message: Message, state: FSMContext, t: ModuleType, lang: str, currency: str
) -> None:
    raw = message.text.strip()
    comment = "" if raw.lower() in t.CANCEL_WORDS else raw

    ok, result = validators.validate_comment(comment)
    if not ok:
        await message.answer(t.ERR_COMMENT_LONG.format(limit=validators.COMMENT_MAX))
        return

    await state.update_data(comment=result)
    data = await state.get_data()

    items = await db.cart_items(message.from_user.id, lang, currency)
    if not items:
        await state.clear()
        await message.answer(
            t.ORDER_CART_VANISHED,
            reply_markup=reply.main_menu(t, is_admin(message.from_user.id)),
        )
        return

    rate = await rates.get(currency)
    summary = _render_confirmation(items, data, t, currency, rate)

    await state.set_state(OrderState.confirm)
    await message.answer(t.ORDER_CHECK, reply_markup=ReplyKeyboardRemove())
    await message.answer(summary, reply_markup=inline.confirm_order(t))


@router.message(OrderState.comment)
async def step_comment_wrong_type(message: Message, t: ModuleType) -> None:
    await message.answer(t.ERR_TEXT_EXPECTED)


def _render_confirmation(
    items: list[dict], data: dict, t: ModuleType, currency: str, rate: float | None
) -> str:
    lines = [t.ORDER_CONFIRM_HEADER]
    for item in items:
        lines.append(
            t.ORDER_CONFIRM_LINE.format(
                title=esc(item["title"]),
                qty=item["quantity"],
                subtotal=format_amount(
                    cart_total_in([item], currency, rate), currency, t
                ),
            )
        )
    total = cart_total_in(items, currency, rate)
    lines.append(
        t.ORDER_CONFIRM_FOOTER.format(
            total=format_amount(total, currency, t),
            name=esc(data["name"]),
            phone=esc(data["phone"]),
            address=esc(data["address"]),
        )
    )
    if data.get("comment"):
        lines.append(t.ORDER_CONFIRM_COMMENT.format(comment=esc(data["comment"])))
    return "\n".join(lines)


# ----------------------------------------------------------------- confirm

@router.callback_query(
    OrderState.confirm, OrderCB.filter(F.action == OrderAction.cancel)
)
async def order_cancel(
    call: CallbackQuery, state: FSMContext, t: ModuleType
) -> None:
    await state.clear()
    await safe_edit(call.message, t.ORDER_CANCELLED)
    await call.message.answer(
        t.MAIN_MENU, reply_markup=reply.main_menu(t, is_admin(call.from_user.id))
    )
    await call.answer()


@router.callback_query(
    OrderState.confirm, OrderCB.filter(F.action == OrderAction.confirm)
)
async def order_confirm(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    t: ModuleType,
    lang: str,
    currency: str,
) -> None:
    data = await state.get_data()
    await state.clear()

    # Snapshot what the customer saw, alongside the base-currency total.
    rate = await rates.get(currency)
    items = await db.cart_items(call.from_user.id, lang, currency)
    display_total = cart_total_in(items, currency, rate) if items else None

    order_id = await db.create_order(
        user_id=call.from_user.id,
        name=data["name"],
        phone=data["phone"],
        address=data["address"],
        comment=data.get("comment", ""),
        display_currency=currency,
        display_total=display_total,
    )

    # Remember the details only once the order actually went through.
    if order_id:
        await db.save_profile(call.from_user.id, data["name"], data["phone"])

    if not order_id:
        await safe_edit(call.message, t.ORDER_CART_VANISHED)
        await call.answer()
        return

    await safe_edit(
        call.message,
        t.ORDER_ACCEPTED.format(order_id=order_id),
        inline.payment_methods(order_id, t),
    )
    await call.message.answer(
        t.MAIN_MENU, reply_markup=reply.main_menu(t, is_admin(call.from_user.id))
    )
    await _notify_new_order(bot, order_id)
    await call.answer()


async def _notify_new_order(bot: Bot, order_id: int) -> None:
    order = await db.get_order(order_id)
    if not order:
        return
    items = await db.get_order_items(order_id)
    a = admin_texts

    lines = [a.ADMIN_NEW_ORDER_HEADER.format(order_id=order_id)]
    for item in items:
        lines.append(
            a.ADMIN_ORDER_ITEM.format(title=esc(item["title"]), qty=item["quantity"])
        )
    lines.append(
        a.ADMIN_ORDER_FOOTER.format(
            total=fmt_price(order["total"]),
            name=esc(order["name"]),
            phone=esc(order["phone"]),
            address=esc(order["address"]),
            created_at=fmt_dt(order["created_at"]),
        )
    )
    if order["comment"]:
        lines.append(a.ORDER_CONFIRM_COMMENT.format(comment=esc(order["comment"])))

    await notify_admins(
        bot, "\n".join(lines), inline.admin_order_actions(order_id, a)
    )


# ----------------------------------------------------------------- history

@router.message(Btn("BTN_MY_ORDERS"))
async def my_orders(message: Message, t: ModuleType) -> None:
    orders = await db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer(t.NO_ORDERS)
        return

    lines = [t.MY_ORDERS_HEADER]
    for order in orders:
        lines.append(
            t.MY_ORDERS_LINE.format(
                order_id=order["id"],
                total=fmt_price(order["total"]),
                status=t.status_label(order["status"]),
                created_at=fmt_dt(order["created_at"]),
            )
        )
    await message.answer("\n".join(lines))
