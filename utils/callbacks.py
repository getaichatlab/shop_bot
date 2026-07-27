"""CallbackData factories.

Rule 3.2.11: callback_data coming from a user is untrusted input. Using aiogram's
CallbackData factory gives us parsing + type validation for free, and keeps every
payload well under the 64-byte Telegram limit.
"""
from __future__ import annotations

from enum import Enum

from aiogram.filters.callback_data import CallbackData


class LanguageCB(CallbackData, prefix="lng"):
    lang: str


class CurrencyCB(CallbackData, prefix="cur"):
    code: str


class RateCB(CallbackData, prefix="rate"):
    """Admin rate management. `code` is empty for the refresh action."""
    action: str          # 'refresh' | 'edit'
    code: str = ""


class CategoryCB(CallbackData, prefix="cat"):
    category_id: int


class ProductCB(CallbackData, prefix="prd"):
    product_id: int
    category_id: int


class CartAddCB(CallbackData, prefix="cadd"):
    product_id: int


class CartQtyCB(CallbackData, prefix="cqty"):
    product_id: int
    delta: int


class CartDelCB(CallbackData, prefix="cdel"):
    product_id: int


class NavAction(str, Enum):
    categories = "categories"
    cart_clear = "cart_clear"
    checkout = "checkout"
    noop = "noop"


class NavCB(CallbackData, prefix="nav"):
    action: NavAction


class OrderAction(str, Enum):
    confirm = "confirm"
    cancel = "cancel"
    # Re-ask for name and phone instead of reusing the saved profile.
    edit_profile = "edit"


class OrderCB(CallbackData, prefix="ord"):
    action: OrderAction


class PayCB(CallbackData, prefix="pay"):
    """`method` is a provider code from payments/providers.py."""
    order_id: int
    method: str


class ReceiptCB(CallbackData, prefix="rcpt"):
    """Admin review of a manual transfer."""
    request_id: int
    approve: bool


class OrderStatus(str, Enum):
    accepted = "accepted"
    shipping = "shipping"
    done = "done"
    canceled = "canceled"


class AdminStatusCB(CallbackData, prefix="ast"):
    order_id: int
    status: OrderStatus


class AdminCategoryCB(CallbackData, prefix="acat"):
    category_id: int


class BroadcastAction(str, Enum):
    send = "send"
    cancel = "cancel"


class BroadcastCB(CallbackData, prefix="bc"):
    action: BroadcastAction
