"""Start, help, cancel, contacts, language switching, main-menu navigation."""
from __future__ import annotations

import logging
from types import ModuleType

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from currencies import BASE_CURRENCY
from database import db
from filters import Btn, is_admin
from keyboards import inline, reply
from locales import get_texts, is_supported
from middlewares.i18n import I18nMiddleware
from services.rates import rates
from currencies import is_supported as currency_supported
from utils.callbacks import CurrencyCB, LanguageCB, NavAction, NavCB
from utils.formatters import esc
from utils.notifier import safe_edit

router = Router(name="common")
log = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, t: ModuleType, lang: str
) -> None:
    """Safe to run repeatedly: upsert_user creates no duplicates."""
    await state.clear()
    await db.upsert_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        language=lang,
    )
    await message.answer(
        t.WELCOME.format(name=esc(message.from_user.first_name)),
        reply_markup=reply.main_menu(t, is_admin(message.from_user.id)),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, t: ModuleType) -> None:
    await message.answer(t.HELP)


# ----------------------------------------------------------------- language

@router.message(Command("language"))
@router.message(Btn("BTN_LANGUAGE"))
async def choose_language(message: Message, state: FSMContext, t: ModuleType) -> None:
    await state.clear()
    await message.answer(t.CHOOSE_LANGUAGE, reply_markup=inline.language_picker())


@router.callback_query(LanguageCB.filter())
async def set_language(
    call: CallbackQuery, callback_data: LanguageCB, i18n: I18nMiddleware
) -> None:
    new_lang = callback_data.lang

    # Untrusted input: only accept codes we actually ship.
    if not is_supported(new_lang):
        await call.answer()
        return

    await db.set_user_language(call.from_user.id, new_lang)
    i18n.remember(call.from_user.id, new_lang)

    new_t = get_texts(new_lang)
    await safe_edit(call.message, new_t.LANGUAGE_SET)
    await call.message.answer(
        new_t.MAIN_MENU,
        reply_markup=reply.main_menu(new_t, is_admin(call.from_user.id)),
    )
    await call.answer()


# ----------------------------------------------------------------- currency

@router.message(Command("currency"))
@router.message(Btn("BTN_CURRENCY"))
async def choose_currency(message: Message, state: FSMContext, t: ModuleType) -> None:
    await state.clear()
    await message.answer(t.CHOOSE_CURRENCY, reply_markup=inline.currency_picker(t))


@router.callback_query(CurrencyCB.filter())
async def set_currency(
    call: CallbackQuery,
    callback_data: CurrencyCB,
    i18n: I18nMiddleware,
    t: ModuleType,
) -> None:
    code = callback_data.code

    # Untrusted input: only accept currencies we actually support.
    if not currency_supported(code):
        await call.answer()
        return

    await db.set_user_currency(call.from_user.id, code)
    i18n.remember(call.from_user.id, currency=code)

    await safe_edit(
        call.message,
        t.CURRENCY_SET.format(currency=t.CURRENCY_NAMES.get(code, code)),
    )

    # Warn instead of silently showing base prices when no rate exists yet.
    if code != BASE_CURRENCY and await rates.get(code) is None:
        await call.message.answer(t.CURRENCY_RATE_MISSING.format(code=code))

    await call.message.answer(
        t.MAIN_MENU, reply_markup=reply.main_menu(t, is_admin(call.from_user.id))
    )
    await call.answer()


# ----------------------------------------------------------------- misc

@router.message(Command("cancel"))
@router.message(Btn("BTN_CANCEL"))
async def cancel_flow(message: Message, state: FSMContext, t: ModuleType) -> None:
    """Universal escape from any FSM flow."""
    menu = reply.main_menu(t, is_admin(message.from_user.id))
    if await state.get_state() is None:
        await message.answer(t.NOTHING_TO_CANCEL, reply_markup=menu)
        return
    await state.clear()
    await message.answer(t.CANCELLED, reply_markup=menu)


@router.message(Btn("BTN_CONTACTS"))
async def contacts(message: Message, t: ModuleType) -> None:
    await message.answer(t.CONTACTS)


@router.message(Btn("BTN_BACK_MAIN"))
async def back_to_main(message: Message, state: FSMContext, t: ModuleType) -> None:
    await state.clear()
    await message.answer(
        t.MAIN_MENU, reply_markup=reply.main_menu(t, is_admin(message.from_user.id))
    )


@router.callback_query(NavCB.filter(F.action == NavAction.noop))
async def noop(call: CallbackQuery) -> None:
    await call.answer()
