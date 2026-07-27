"""FSM state groups. Every multi-step flow has a cancel escape (rule 3.6)."""
from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    """Checkout: name -> phone -> address -> comment -> confirm."""
    name = State()
    phone = State()
    address = State()
    comment = State()
    confirm = State()


class AddCategoryState(StatesGroup):
    # One title per shipped language; the handler loops over LANGUAGE_ORDER.
    title = State()


class AddProductState(StatesGroup):
    category = State()
    title = State()          # asked once per language
    description = State()    # asked once per language
    price = State()          # base currency
    price_currency = State() # asked once per extra currency, "auto" allowed
    photo = State()


class RateState(StatesGroup):
    value = State()


class ReceiptState(StatesGroup):
    """Waiting for a photo of a bank transfer receipt."""
    photo = State()


class BroadcastState(StatesGroup):
    message = State()
    confirm = State()
