"""Catalog browsing: categories -> products -> product card."""
from __future__ import annotations

import logging
from types import ModuleType

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database import db
from filters import Btn
from keyboards import inline
from utils.callbacks import CartAddCB, CategoryCB, NavAction, NavCB, ProductCB
from services.rates import rates
from utils.formatters import esc
from utils.money import cart_total_in, format_amount, price_text
from utils.notifier import safe_edit

router = Router(name="catalog")
log = logging.getLogger(__name__)


@router.message(Btn("BTN_CATALOG"))
async def show_categories(message: Message, t: ModuleType, lang: str) -> None:
    categories = await db.get_categories(lang)
    if not categories:
        await message.answer(t.CATALOG_EMPTY)
        return
    await message.answer(
        t.CHOOSE_CATEGORY, reply_markup=inline.categories(categories, t)
    )


@router.callback_query(NavCB.filter(F.action == NavAction.categories))
async def back_to_categories(call: CallbackQuery, t: ModuleType, lang: str) -> None:
    categories = await db.get_categories(lang)
    if not categories:
        await call.answer(t.CATALOG_EMPTY, show_alert=True)
        return
    await safe_edit(call.message, t.CHOOSE_CATEGORY, inline.categories(categories, t))
    await call.answer()


@router.callback_query(CategoryCB.filter())
async def show_products(
    call: CallbackQuery,
    callback_data: CategoryCB,
    t: ModuleType,
    lang: str,
    currency: str,
) -> None:
    category_id = callback_data.category_id

    # Untrusted input: the category may have been deleted since the keyboard was sent.
    if not await db.category_exists(category_id):
        await call.answer(t.CATEGORY_EMPTY, show_alert=True)
        return

    products = await db.get_products(category_id, lang, currency)
    if not products:
        await call.answer(t.CATEGORY_EMPTY, show_alert=True)
        return

    rate = await rates.get(currency)
    markup = inline.products(products, category_id, t, currency, rate)

    # A product card is a photo message; edit_text cannot be used on it.
    if call.message.photo:
        try:
            await call.message.delete()
        except Exception:
            log.debug("Could not delete product card")
        await call.message.answer(t.CHOOSE_PRODUCT, reply_markup=markup)
    else:
        await safe_edit(call.message, t.CHOOSE_PRODUCT, markup)
    await call.answer()


@router.callback_query(ProductCB.filter())
async def product_card(
    call: CallbackQuery,
    callback_data: ProductCB,
    t: ModuleType,
    lang: str,
    currency: str,
) -> None:
    product = await db.get_product(callback_data.product_id, lang, currency)
    if not product:
        await call.answer(t.PRODUCT_NOT_FOUND, show_alert=True)
        return

    caption = t.PRODUCT_CARD.format(
        title=esc(product["title"]),
        description=esc(product["description"]) or t.NO_DESCRIPTION,
        price=price_text(
            product["price"],
            currency,
            await rates.get(currency),
            t,
            product["price_override"],
        ),
    )
    markup = inline.product_card(product["id"], product["category_id"], t)

    try:
        await call.message.delete()
    except Exception:
        log.debug("Could not delete list message")

    if product["photo_id"]:
        try:
            await call.message.answer_photo(
                photo=product["photo_id"], caption=caption, reply_markup=markup
            )
        except Exception as e:
            # Photo file_id can expire; fall back to a text card.
            log.warning("Photo send failed for product %s: %s", product["id"], e)
            await call.message.answer(caption, reply_markup=markup)
    else:
        await call.message.answer(caption, reply_markup=markup)
    await call.answer()


@router.callback_query(CartAddCB.filter())
async def add_to_cart(
    call: CallbackQuery,
    callback_data: CartAddCB,
    t: ModuleType,
    lang: str,
    currency: str,
) -> None:
    ok = await db.cart_add(call.from_user.id, callback_data.product_id)
    if not ok:
        await call.answer(t.PRODUCT_NOT_FOUND, show_alert=True)
        return
    items = await db.cart_items(call.from_user.id, lang, currency)
    rate = await rates.get(currency)
    total = cart_total_in(items, currency, rate)
    await call.answer(
        t.ADDED_TO_CART.format(total=format_amount(total, currency, t)),
        show_alert=True,
    )
