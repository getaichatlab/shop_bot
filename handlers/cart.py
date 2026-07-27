"""Shopping cart: view, quantity changes, removal, clearing."""
from __future__ import annotations

import logging
from types import ModuleType

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database import db
from filters import Btn
from keyboards import inline
from utils.callbacks import CartDelCB, CartQtyCB, NavAction, NavCB
from services.rates import rates
from utils.formatters import esc
from utils.money import cart_total_in, format_amount, price_text
from utils.notifier import safe_edit

router = Router(name="cart")
log = logging.getLogger(__name__)

MAX_QTY_PER_ITEM = 99


def render_cart(
    items: list[dict], t: ModuleType, currency: str, rate: float | None
) -> str:
    """Render the cart in the customer's currency.

    Line subtotals are computed per line and then summed, so the total always
    matches what the customer can add up on screen.
    """
    lines = [t.CART_HEADER]
    for item in items:
        override = item.get("price_override")
        unit = price_text(item["price"], currency, rate, t, override)
        subtotal_minor = cart_total_in([item], currency, rate)
        lines.append(
            t.CART_LINE.format(
                title=esc(item["title"]),
                qty=item["quantity"],
                price=unit,
                subtotal=format_amount(subtotal_minor, currency, t),
            )
        )
    total = cart_total_in(items, currency, rate)
    lines.append(t.CART_TOTAL.format(total=format_amount(total, currency, t)))
    return "\n".join(lines)


@router.message(Btn("BTN_CART"))
async def show_cart(
    message: Message, t: ModuleType, lang: str, currency: str
) -> None:
    items = await db.cart_items(message.from_user.id, lang, currency)
    if not items:
        await message.answer(t.CART_EMPTY)
        return
    rate = await rates.get(currency)
    await message.answer(
        render_cart(items, t, currency, rate), reply_markup=inline.cart(items, t)
    )


async def refresh_cart(
    call: CallbackQuery, t: ModuleType, lang: str, currency: str
) -> None:
    items = await db.cart_items(call.from_user.id, lang, currency)
    if not items:
        await safe_edit(call.message, t.CART_EMPTY)
        return
    rate = await rates.get(currency)
    await safe_edit(
        call.message, render_cart(items, t, currency, rate), inline.cart(items, t)
    )


@router.callback_query(CartQtyCB.filter())
async def change_quantity(
    call: CallbackQuery, callback_data: CartQtyCB, t: ModuleType, lang: str, currency: str
) -> None:
    items = {
        i["product_id"]: i["quantity"]
        for i in await db.cart_items(call.from_user.id, lang, currency)
    }
    current = items.get(callback_data.product_id)

    if current is None:
        await call.answer(t.PRODUCT_NOT_FOUND, show_alert=True)
        await refresh_cart(call, t, lang, currency)
        return

    new_qty = current + callback_data.delta
    if new_qty > MAX_QTY_PER_ITEM:
        await call.answer(f"max {MAX_QTY_PER_ITEM}", show_alert=True)
        return

    await db.cart_set_qty(call.from_user.id, callback_data.product_id, new_qty)
    await refresh_cart(call, t, lang, currency)
    await call.answer()


@router.callback_query(CartDelCB.filter())
async def remove_item(
    call: CallbackQuery,
    callback_data: CartDelCB,
    t: ModuleType,
    lang: str,
    currency: str,
) -> None:
    await db.cart_remove(call.from_user.id, callback_data.product_id)
    await refresh_cart(call, t, lang, currency)
    await call.answer(t.ITEM_REMOVED)


@router.callback_query(NavCB.filter(F.action == NavAction.cart_clear))
async def clear_cart(call: CallbackQuery, t: ModuleType) -> None:
    await db.cart_clear(call.from_user.id)
    await safe_edit(call.message, t.CART_CLEARED)
    await call.answer()
