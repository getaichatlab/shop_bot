"""Admin panel: catalog management, orders, statistics, broadcast.

Every handler in this router is behind the IsAdmin filter, applied once at the
router level (rule 3.2.4).
"""
from __future__ import annotations

import logging
from types import ModuleType

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from currencies import BASE_CURRENCY, CURRENCY_ORDER, get_currency
from currencies import is_supported as currency_supported
from database import db
from filters import Btn, IsAdmin
from keyboards import inline, reply
from locales import LANGUAGE_ORDER, get_texts, language_name
from services.rates import rates, refresh_rates
from states import AddCategoryState, AddProductState, BroadcastState, RateState
from utils import validators
from utils.broadcast import broadcast_copy
from utils.callbacks import (
    AdminCategoryCB,
    AdminStatusCB,
    BroadcastAction,
    BroadcastCB,
    RateCB,
)
from utils.formatters import esc, fmt_dt, fmt_price
from utils.money import convert, format_amount
from utils.notifier import safe_edit, safe_send

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

log = logging.getLogger(__name__)


# ----------------------------------------------------------------- i18n input
#
# Catalog text is business data, so it cannot be translated by the bot: the
# admin supplies it once per shipped language. These helpers walk through
# LANGUAGE_ORDER one language at a time, keeping the collected values in FSM
# data under `key`.

def _next_language(collected: dict[str, str]) -> str | None:
    """The first language that has not been filled in yet."""
    for code in LANGUAGE_ORDER:
        if code not in collected:
            return code
    return None


async def _ask_in_language(
    message: Message, template: str, lang_code: str
) -> None:
    await message.answer(template.format(language=language_name(lang_code)))


@router.message(Btn("BTN_ADMIN"))
async def open_panel(message: Message, state: FSMContext, t: ModuleType) -> None:
    await state.clear()
    await message.answer(t.ADMIN_PANEL, reply_markup=reply.admin_menu(t))


# ----------------------------------------------------------------- stats

@router.message(Command("stats"))
@router.message(Btn("BTN_STATS"))
async def show_stats(message: Message, t: ModuleType) -> None:
    data = await db.stats()
    await message.answer(
        t.ADMIN_STATS.format(
            users=data["users"],
            active=data["active"],
            products=data["products"],
            orders=data["orders"],
            paid=data["paid"],
            revenue=fmt_price(data["revenue"], t),
        )
    )


# ----------------------------------------------------------------- orders

@router.message(Btn("BTN_ORDERS"))
async def show_orders(message: Message, t: ModuleType) -> None:
    orders = await db.get_recent_orders(limit=10)
    if not orders:
        await message.answer(t.ADMIN_NO_ORDERS)
        return

    for order in orders:
        items = await db.get_order_items(order["id"])
        lines = [
            t.ADMIN_ORDER_HEADER.format(
                order_id=order["id"], status=t.status_label(order["status"])
            )
        ]
        for item in items:
            lines.append(
                t.ADMIN_ORDER_ITEM.format(
                    title=esc(item["title"]), qty=item["quantity"]
                )
            )
        lines.append(
            t.ADMIN_ORDER_FOOTER.format(
                total=fmt_price(order["total"], t),
                name=esc(order["name"]),
                phone=esc(order["phone"]),
                address=esc(order["address"]),
                created_at=fmt_dt(order["created_at"]),
            )
        )
        if order["comment"]:
            lines.append(t.ORDER_CONFIRM_COMMENT.format(comment=esc(order["comment"])))
        await message.answer(
            "\n".join(lines), reply_markup=inline.admin_order_actions(order["id"], t)
        )


@router.callback_query(AdminStatusCB.filter())
async def change_status(
    call: CallbackQuery, callback_data: AdminStatusCB, bot: Bot, t: ModuleType
) -> None:
    order = await db.get_order(callback_data.order_id)
    if not order:
        await call.answer(t.PAY_ORDER_NOT_FOUND, show_alert=True)
        return

    new_status = callback_data.status.value
    await db.set_order_status(order["id"], new_status)
    await call.answer(t.ADMIN_STATUS_SET.format(status=t.status_label(new_status)))

    # Notify the customer — in the customer's own language.
    from locales import get_texts

    customer_lang = await db.get_user_language(order["user_id"])
    ct = get_texts(customer_lang)
    delivered = await safe_send(
        bot,
        order["user_id"],
        ct.ORDER_STATUS_CHANGED.format(
            order_id=order["id"], status=ct.status_label(new_status)
        ),
    )
    if not delivered:
        await db.deactivate_user(order["user_id"])

    # Refresh the admin card header, in the admin's language.
    body = call.message.html_text.split("\n", 1)
    tail = body[1] if len(body) > 1 else ""
    await safe_edit(
        call.message,
        t.ADMIN_ORDER_HEADER.format(
            order_id=order["id"], status=t.status_label(new_status)
        )
        + "\n"
        + tail,
        inline.admin_order_actions(order["id"], t),
    )


# ----------------------------------------------------------------- category

@router.message(Btn("BTN_ADD_CATEGORY"))
async def add_category_start(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    await state.set_state(AddCategoryState.title)
    await state.update_data(titles={})
    await message.answer(
        t.ADMIN_ASK_CATEGORY_NAME.format(language=language_name(LANGUAGE_ORDER[0])),
        reply_markup=reply.cancel_only(t),
    )


@router.message(AddCategoryState.title, F.text)
async def add_category_title(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    ok, result = validators.validate_title(message.text)
    if not ok:
        await message.answer(t.ERR_TEXT_EXPECTED)
        return

    data = await state.get_data()
    titles: dict[str, str] = dict(data.get("titles", {}))
    current = _next_language(titles)
    if current is None:  # defensive: state out of sync
        await state.clear()
        return
    titles[current] = result
    await state.update_data(titles=titles)

    following = _next_language(titles)
    if following is not None:
        await _ask_in_language(message, t.ADMIN_ASK_CATEGORY_NAME, following)
        return

    await state.clear()
    try:
        await db.add_category(titles)
        await message.answer(
            t.ADMIN_CATEGORY_ADDED.format(
                title=esc(titles.get(settings.default_lang, result))
            ),
            reply_markup=reply.admin_menu(t),
        )
    except Exception:
        await message.answer(
            t.ADMIN_CATEGORY_EXISTS, reply_markup=reply.admin_menu(t)
        )


# ----------------------------------------------------------------- product

@router.message(Btn("BTN_ADD_PRODUCT"))
async def add_product_start(
    message: Message, state: FSMContext, t: ModuleType, lang: str
) -> None:
    categories = await db.get_categories(lang)
    if not categories:
        await message.answer(t.ADMIN_NEED_CATEGORY)
        return
    await state.set_state(AddProductState.category)
    await message.answer(
        t.ADMIN_PICK_CATEGORY, reply_markup=inline.admin_categories(categories, t)
    )


@router.callback_query(AddProductState.category, AdminCategoryCB.filter())
async def add_product_pick_category(
    call: CallbackQuery,
    callback_data: AdminCategoryCB,
    state: FSMContext,
    t: ModuleType,
) -> None:
    if not await db.category_exists(callback_data.category_id):
        await call.answer(t.CATEGORY_EMPTY, show_alert=True)
        return
    await state.update_data(category_id=callback_data.category_id, titles={}, descriptions={})
    await state.set_state(AddProductState.title)
    await safe_edit(
        call.message,
        t.ADMIN_ASK_PRODUCT_TITLE.format(language=language_name(LANGUAGE_ORDER[0])),
    )
    await call.answer()


@router.message(AddProductState.title, F.text)
async def add_product_title(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    ok, result = validators.validate_title(message.text)
    if not ok:
        await message.answer(t.ERR_TEXT_EXPECTED)
        return

    data = await state.get_data()
    titles: dict[str, str] = dict(data.get("titles", {}))
    current = _next_language(titles)
    if current is None:
        await state.clear()
        return
    titles[current] = result
    await state.update_data(titles=titles)

    following = _next_language(titles)
    if following is not None:
        await _ask_in_language(message, t.ADMIN_ASK_PRODUCT_TITLE, following)
        return

    await state.set_state(AddProductState.description)
    await _ask_in_language(message, t.ADMIN_ASK_PRODUCT_DESC, LANGUAGE_ORDER[0])


@router.message(AddProductState.description, F.text)
async def add_product_description(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    raw = message.text.strip()
    value = "" if raw.lower() in t.CANCEL_WORDS else raw
    ok, result = validators.validate_description(value)
    if not ok:
        await message.answer(
            t.ERR_COMMENT_LONG.format(limit=validators.DESCRIPTION_MAX)
        )
        return

    data = await state.get_data()
    descriptions: dict[str, str] = dict(data.get("descriptions", {}))
    current = _next_language(descriptions)
    if current is None:
        await state.clear()
        return
    descriptions[current] = result
    await state.update_data(descriptions=descriptions)

    following = _next_language(descriptions)
    if following is not None:
        await _ask_in_language(message, t.ADMIN_ASK_PRODUCT_DESC, following)
        return

    await state.set_state(AddProductState.price)
    await message.answer(t.ADMIN_ASK_PRODUCT_PRICE)


EXTRA_CURRENCIES = [c for c in CURRENCY_ORDER if c != BASE_CURRENCY]


async def _ask_price_for(message: Message, t: ModuleType, code: str, base_price: int) -> None:
    """Prompt for one currency, showing the rate-based figure as a hint."""
    rate = await rates.get(code)
    try:
        suggested = format_amount(convert(base_price, code, rate), code, t)
    except Exception:
        suggested = "—"

    await message.answer(
        t.ADMIN_ASK_PRICE_CURRENCY.format(
            name=t.CURRENCY_NAMES.get(code, code),
            auto=t.BTN_PRICE_AUTO,
            suggested=suggested,
        ),
        reply_markup=reply.price_auto(t),
    )


@router.message(AddProductState.price, F.text)
async def add_product_price(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    price = validators.parse_price(message.text)
    if price is None:
        await message.answer(t.ERR_PRICE_INVALID)
        return
    await state.update_data(price=price, prices={})

    if not EXTRA_CURRENCIES:
        await state.set_state(AddProductState.photo)
        await message.answer(t.ADMIN_ASK_PRODUCT_PHOTO)
        return

    await state.set_state(AddProductState.price_currency)
    await _ask_price_for(message, t, EXTRA_CURRENCIES[0], price)


@router.message(AddProductState.price_currency, F.text)
async def add_product_price_currency(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    data = await state.get_data()
    prices: dict[str, int] = dict(data.get("prices", {}))
    done = {code for code in EXTRA_CURRENCIES if code in prices or code in data.get("auto", [])}
    auto: list[str] = list(data.get("auto", []))

    pending = [code for code in EXTRA_CURRENCIES if code not in done]
    if not pending:
        await state.set_state(AddProductState.photo)
        await message.answer(t.ADMIN_ASK_PRODUCT_PHOTO)
        return

    current = pending[0]
    text = message.text.strip()

    if text == t.BTN_PRICE_AUTO:
        # Leave it unpinned: the price follows the exchange rate from now on.
        auto.append(current)
    else:
        currency = get_currency(current)
        amount = validators.parse_money(text, currency.decimals)
        if amount is None:
            await message.answer(t.ERR_PRICE_INVALID)
            return
        prices[current] = amount

    await state.update_data(prices=prices, auto=auto)

    remaining = [
        code for code in EXTRA_CURRENCIES if code not in prices and code not in auto
    ]
    if remaining:
        await _ask_price_for(message, t, remaining[0], data["price"])
        return

    await state.set_state(AddProductState.photo)
    await message.answer(t.ADMIN_ASK_PRODUCT_PHOTO, reply_markup=reply.cancel_only(t))


@router.message(AddProductState.photo, F.photo)
async def add_product_photo(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    await _save_product(message, state, message.photo[-1].file_id, t)


@router.message(AddProductState.photo, F.text)
async def add_product_without_photo(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    if message.text.strip().lower() not in t.CANCEL_WORDS:
        await message.answer(t.ADMIN_NEED_PHOTO_OR_NO)
        return
    await _save_product(message, state, None, t)


async def _save_product(
    message: Message, state: FSMContext, photo_id: str | None, t: ModuleType
) -> None:
    data = await state.get_data()
    await state.clear()

    titles: dict[str, str] = data["titles"]
    descriptions: dict[str, str] = data.get("descriptions", {})

    await db.add_product(
        category_id=data["category_id"],
        titles=titles,
        descriptions=descriptions,
        price=data["price"],
        photo_id=photo_id,
        prices=data.get("prices") or None,
    )
    await message.answer(
        t.ADMIN_PRODUCT_ADDED.format(
            title=esc(titles.get(t.LANG_CODE) or next(iter(titles.values()))),
            price=fmt_price(data["price"], t),
        ),
        reply_markup=reply.admin_menu(t),
    )


# ----------------------------------------------------------------- rates

async def _render_rates(t: ModuleType) -> str:
    stored = await db.get_rates()
    lines = [t.ADMIN_RATES_HEADER.format(base=BASE_CURRENCY)]

    body = []
    for code in CURRENCY_ORDER:
        if code == BASE_CURRENCY:
            continue
        row = stored.get(code)
        if not row:
            continue
        source = (
            t.RATE_SOURCE_MANUAL if row["source"] == "manual" else t.RATE_SOURCE_API
        )
        body.append(
            t.ADMIN_RATES_LINE.format(
                name=t.CURRENCY_NAMES.get(code, code),
                code=code,
                rate=f"{float(row['rate']):,.2f}".replace(",", " "),
                base=BASE_CURRENCY,
                source=source,
                updated=fmt_dt(row["updated_at"]),
            )
        )

    lines.append("\n\n".join(body) if body else t.ADMIN_RATES_NONE)
    return "\n".join(lines)


@router.message(Command("rates"))
@router.message(Btn("BTN_RATES"))
async def show_rates(message: Message, state: FSMContext, t: ModuleType) -> None:
    await state.clear()
    await message.answer(await _render_rates(t), reply_markup=inline.admin_rates(t))


@router.callback_query(RateCB.filter(F.action == "refresh"))
async def refresh_rates_handler(call: CallbackQuery, t: ModuleType) -> None:
    await call.answer(t.LOADING)
    count = await refresh_rates()

    if count:
        await call.message.answer(t.ADMIN_RATES_REFRESH_OK.format(count=count))
    else:
        await call.message.answer(t.ADMIN_RATES_REFRESH_FAIL)

    await safe_edit(call.message, await _render_rates(t), inline.admin_rates(t))


@router.callback_query(RateCB.filter(F.action == "edit"))
async def edit_rate_start(
    call: CallbackQuery, callback_data: RateCB, state: FSMContext, t: ModuleType
) -> None:
    code = callback_data.code
    if not currency_supported(code) or code == BASE_CURRENCY:
        await call.answer()
        return

    await state.set_state(RateState.value)
    await state.update_data(rate_code=code)
    await call.message.answer(
        t.ADMIN_ASK_RATE.format(code=code, base=BASE_CURRENCY),
        reply_markup=reply.cancel_only(t),
    )
    await call.answer()


@router.message(RateState.value, F.text)
async def edit_rate_finish(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    value = validators.parse_rate(message.text)
    if value is None:
        await message.answer(t.ADMIN_RATE_INVALID)
        return

    data = await state.get_data()
    code = data["rate_code"]
    await state.clear()

    # source='manual' keeps the API refresh from overwriting this number.
    await db.set_rate(code, value, source="manual")
    rates.invalidate()

    await message.answer(
        t.ADMIN_RATE_SET.format(code=code, rate=value, base=BASE_CURRENCY),
        reply_markup=reply.admin_menu(t),
    )


# ----------------------------------------------------------------- broadcast

@router.message(Btn("BTN_BROADCAST"))
async def broadcast_start(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    await state.set_state(BroadcastState.message)
    await message.answer(t.ADMIN_ASK_BROADCAST, reply_markup=reply.cancel_only(t))


@router.message(BroadcastState.message)
async def broadcast_preview(
    message: Message, state: FSMContext, t: ModuleType
) -> None:
    if message.text and message.text.strip() == t.BTN_CANCEL:
        await state.clear()
        await message.answer(
            t.ADMIN_BROADCAST_CANCELLED, reply_markup=reply.admin_menu(t)
        )
        return

    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
    recipients = await db.get_active_user_ids()
    await state.set_state(BroadcastState.confirm)
    await message.answer(
        t.ADMIN_BROADCAST_CONFIRM.format(total=len(recipients)),
        reply_markup=inline.broadcast_confirm(t),
    )


@router.callback_query(
    BroadcastState.confirm, BroadcastCB.filter(F.action == BroadcastAction.cancel)
)
async def broadcast_cancel(
    call: CallbackQuery, state: FSMContext, t: ModuleType
) -> None:
    await state.clear()
    await safe_edit(call.message, t.ADMIN_BROADCAST_CANCELLED)
    await call.answer()


@router.callback_query(
    BroadcastState.confirm, BroadcastCB.filter(F.action == BroadcastAction.send)
)
async def broadcast_send(
    call: CallbackQuery, state: FSMContext, bot: Bot, t: ModuleType
) -> None:
    data = await state.get_data()
    await state.clear()
    await safe_edit(call.message, t.ADMIN_BROADCAST_STARTED)
    await call.answer()

    user_ids = await db.get_active_user_ids()
    result = await broadcast_copy(
        bot=bot,
        user_ids=user_ids,
        from_chat_id=data["from_chat_id"],
        message_id=data["message_id"],
        on_blocked=db.deactivate_user,
    )

    await call.message.answer(
        t.ADMIN_BROADCAST_DONE.format(
            sent=result.sent, failed=result.failed, seconds=result.seconds
        ),
        reply_markup=reply.admin_menu(t),
    )
