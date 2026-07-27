"""Reply keyboards. Every builder receives the caller's locale module `t`."""
from __future__ import annotations

from types import ModuleType

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu(t: ModuleType, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=t.BTN_CATALOG), KeyboardButton(text=t.BTN_CART)],
        [KeyboardButton(text=t.BTN_MY_ORDERS), KeyboardButton(text=t.BTN_CONTACTS)],
        [KeyboardButton(text=t.BTN_LANGUAGE), KeyboardButton(text=t.BTN_CURRENCY)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=t.BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def phone_request(t: ModuleType) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_SEND_PHONE, request_contact=True)],
            [KeyboardButton(text=t.BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_only(t: ModuleType) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.BTN_CANCEL)]],
        resize_keyboard=True,
    )


def address_with_edit(t: ModuleType) -> ReplyKeyboardMarkup:
    """Address step for a returning customer: continue, or fix the details."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_EDIT_PROFILE)],
            [KeyboardButton(text=t.BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def price_auto(t: ModuleType) -> ReplyKeyboardMarkup:
    """Type an exact price, or let the exchange rate decide."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_PRICE_AUTO)],
            [KeyboardButton(text=t.BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def admin_menu(t: ModuleType) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t.BTN_ADD_PRODUCT),
                KeyboardButton(text=t.BTN_ADD_CATEGORY),
            ],
            [KeyboardButton(text=t.BTN_ORDERS), KeyboardButton(text=t.BTN_STATS)],
            [KeyboardButton(text=t.BTN_RATES), KeyboardButton(text=t.BTN_BROADCAST)],
            [KeyboardButton(text=t.BTN_BACK_MAIN)],
        ],
        resize_keyboard=True,
    )
