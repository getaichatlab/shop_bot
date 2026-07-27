"""Inline keyboards.

Every callback payload is built by a CallbackData factory, so the payload is
language-independent — only the visible label changes with the locale.
"""
from __future__ import annotations

from types import ModuleType

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from currencies import BASE_CURRENCY, CURRENCY_ORDER
from payments import PROVIDERS, by_region, enabled_codes
from locales import LANGUAGE_ORDER, get_texts
from utils.callbacks import (
    AdminCategoryCB,
    AdminStatusCB,
    BroadcastAction,
    BroadcastCB,
    CartAddCB,
    CartDelCB,
    CartQtyCB,
    CategoryCB,
    CurrencyCB,
    LanguageCB,
    NavAction,
    NavCB,
    OrderAction,
    OrderCB,
    OrderStatus,
    PayCB,
    ProductCB,
    RateCB,
    ReceiptCB,
)
from utils.money import price_text

# Telegram truncates long button labels; keep cart labels readable.
CART_LABEL_LIMIT = 18


def language_picker() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code in LANGUAGE_ORDER:
        kb.button(text=get_texts(code).LANG_NAME, callback_data=LanguageCB(lang=code))
    kb.adjust(1)
    return kb.as_markup()


def currency_picker(t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code in CURRENCY_ORDER:
        kb.button(
            text=t.CURRENCY_NAMES.get(code, code),
            callback_data=CurrencyCB(code=code),
        )
    kb.adjust(1)
    return kb.as_markup()


def admin_rates(t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=t.ADMIN_BTN_REFRESH_RATES,
        callback_data=RateCB(action="refresh"),
    )
    for code in CURRENCY_ORDER:
        if code == BASE_CURRENCY:
            continue
        kb.button(
            text=t.ADMIN_BTN_EDIT_RATE.format(code=code),
            callback_data=RateCB(action="edit", code=code),
        )
    kb.adjust(1, 2)
    return kb.as_markup()


def categories(items: list[dict], t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(text=item["title"], callback_data=CategoryCB(category_id=item["id"]))
    kb.adjust(2)
    return kb.as_markup()


def products(
    items: list[dict],
    category_id: int,
    t: ModuleType,
    currency: str = BASE_CURRENCY,
    rate: float | None = None,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        price = price_text(item["price"], currency, rate, t, item.get("price_override"))
        kb.button(
            text=f"{item['title']} — {price}",
            callback_data=ProductCB(product_id=item["id"], category_id=category_id),
        )
    kb.button(
        text=t.BTN_BACK_CATEGORIES, callback_data=NavCB(action=NavAction.categories)
    )
    kb.adjust(1)
    return kb.as_markup()


def product_card(
    product_id: int, category_id: int, t: ModuleType
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.BTN_ADD_TO_CART, callback_data=CartAddCB(product_id=product_id))
    kb.button(text=t.BTN_BACK, callback_data=CategoryCB(category_id=category_id))
    kb.adjust(1)
    return kb.as_markup()


def cart(items: list[dict], t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        pid = item["product_id"]
        label = item["title"][:CART_LABEL_LIMIT]
        kb.row(
            InlineKeyboardButton(
                text="➖", callback_data=CartQtyCB(product_id=pid, delta=-1).pack()
            ),
            InlineKeyboardButton(
                text=f"{label} ×{item['quantity']}",
                callback_data=NavCB(action=NavAction.noop).pack(),
            ),
            InlineKeyboardButton(
                text="➕", callback_data=CartQtyCB(product_id=pid, delta=1).pack()
            ),
            InlineKeyboardButton(
                text="🗑", callback_data=CartDelCB(product_id=pid).pack()
            ),
        )
    kb.row(
        InlineKeyboardButton(
            text=t.BTN_CHECKOUT, callback_data=NavCB(action=NavAction.checkout).pack()
        )
    )
    kb.row(
        InlineKeyboardButton(
            text=t.BTN_CLEAR_CART,
            callback_data=NavCB(action=NavAction.cart_clear).pack(),
        )
    )
    return kb.as_markup()


def confirm_order(t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.BTN_CONFIRM, callback_data=OrderCB(action=OrderAction.confirm))
    kb.button(text=t.BTN_CANCEL, callback_data=OrderCB(action=OrderAction.cancel))
    kb.adjust(2)
    return kb.as_markup()


def payment_methods(order_id: int, t: ModuleType) -> InlineKeyboardMarkup:
    """One button per enabled provider, grouped so nobody scrolls past
    another country's methods to reach their own."""
    kb = InlineKeyboardBuilder()
    grouped = by_region(enabled_codes())

    for region in ("uz", "cis", "global"):
        codes = grouped.get(region, [])
        for code in codes:
            provider = PROVIDERS[code]
            kb.button(
                text=getattr(t, provider.label_key),
                callback_data=PayCB(order_id=order_id, method=code),
            )
    # Two per row for the country blocks, one per row for the universal ones.
    uz_count = len(grouped.get("uz", []))
    cis_count = len(grouped.get("cis", []))
    layout = []
    for count in (uz_count, cis_count):
        layout += [2] * (count // 2) + ([1] if count % 2 else [])
    layout += [1] * len(grouped.get("global", []))
    kb.adjust(*(layout or [1]))
    return kb.as_markup()


def demo_fallback(order_id: int, region: str, t: ModuleType) -> InlineKeyboardMarkup:
    """After a demo walkthrough, offer the transfer route that does work."""
    kb = InlineKeyboardBuilder()
    fallback = "card_uz" if region == "uz" else "sbp"
    if fallback in enabled_codes():
        kb.button(
            text=t.BTN_PAY_BY_RECEIPT,
            callback_data=PayCB(order_id=order_id, method=fallback),
        )
    if "cash" in enabled_codes():
        kb.button(
            text=t.BTN_PAY_CASH,
            callback_data=PayCB(order_id=order_id, method="cash"),
        )
    kb.adjust(1)
    return kb.as_markup()


def receipt_review(request_id: int, t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text=t.BTN_RECEIPT_APPROVE,
        callback_data=ReceiptCB(request_id=request_id, approve=True),
    )
    kb.button(
        text=t.BTN_RECEIPT_REJECT,
        callback_data=ReceiptCB(request_id=request_id, approve=False),
    )
    kb.adjust(2)
    return kb.as_markup()


def admin_order_actions(order_id: int, t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for label, status in (
        (t.BTN_ST_ACCEPTED, OrderStatus.accepted),
        (t.BTN_ST_SHIPPING, OrderStatus.shipping),
        (t.BTN_ST_DONE, OrderStatus.done),
        (t.BTN_ST_CANCELED, OrderStatus.canceled),
    ):
        kb.button(
            text=label, callback_data=AdminStatusCB(order_id=order_id, status=status)
        )
    kb.adjust(2)
    return kb.as_markup()


def admin_categories(items: list[dict], t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(
            text=item["title"], callback_data=AdminCategoryCB(category_id=item["id"])
        )
    kb.adjust(2)
    return kb.as_markup()


def broadcast_confirm(t: ModuleType) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.BTN_SEND, callback_data=BroadcastCB(action=BroadcastAction.send))
    kb.button(
        text=t.BTN_CANCEL, callback_data=BroadcastCB(action=BroadcastAction.cancel)
    )
    kb.adjust(2)
    return kb.as_markup()
