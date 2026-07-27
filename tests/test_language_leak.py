"""Regression guard against language leaking between locales.

The bug this file exists for: the bot answered in Russian, but the inline
keyboard still showed Uzbek category names, because catalog data was seeded in
one language only. These tests drive a full session in one language and fail if
a single marker of the other language appears anywhere in the output.
"""
from __future__ import annotations

import pytest

from currencies import BASE_CURRENCY
from locales import LOCALES, get_texts
from tests.conftest import ADMIN_ID, USER_ID
from tests.mocks import callback_update, make_bot, message_update
from tests.test_flow import build, feed

pytestmark = pytest.mark.asyncio

RU = get_texts("ru")
UZ = get_texts("uz")

# Words that can only come from the demo catalog or the currency symbol of one
# specific language. Product model names (iPhone, MacBook) are intentionally
# untranslated and are therefore not listed.
UZBEK_MARKERS = [
    "Smartfonlar",
    "Noutbuklar",
    "Aksessuarlar",
    "so'm",
    "kafolat",
    "Simsiz",
    "quvvatlash",
]

RUSSIAN_MARKERS = [
    "Смартфоны",
    "Ноутбуки",
    "Аксессуары",
    "сум",
    "гарантия",
    "Беспроводная",
    "зарядка",
]


def collect_output(session) -> str:
    """Every visible string the bot produced: texts, captions and button labels."""
    chunks: list[str] = []
    for call in session.calls:
        for key in ("text", "caption"):
            value = call.data.get(key)
            if value:
                chunks.append(str(value))
        markup = call.data.get("reply_markup")
        if isinstance(markup, dict):
            for row in markup.get("inline_keyboard", []) or []:
                for button in row:
                    if button.get("text"):
                        chunks.append(button["text"])
            for row in markup.get("keyboard", []) or []:
                for button in row:
                    label = button.get("text") if isinstance(button, dict) else button
                    if label:
                        chunks.append(str(label))
    return "\n".join(chunks)


async def browse_everything(dp, bot, db, lang: str) -> None:
    """Walk the whole customer surface: menu, catalog, product card, cart."""
    t = get_texts(lang)

    await feed(dp, bot, message_update(USER_ID, "/start"))
    if lang != "ru":
        await feed(dp, bot, callback_update(USER_ID, f"lng:{lang}"))

    await feed(dp, bot, message_update(USER_ID, "/help"))
    await feed(dp, bot, message_update(USER_ID, t.BTN_CONTACTS))
    await feed(dp, bot, message_update(USER_ID, t.BTN_CATALOG))

    for category in await db.get_categories(lang):
        await feed(dp, bot, callback_update(USER_ID, f"cat:{category['id']}"))
        for product in await db.get_products(category["id"], lang):
            await feed(
                dp,
                bot,
                callback_update(
                    USER_ID, f"prd:{product['id']}:{category['id']}"
                ),
            )
            await feed(dp, bot, callback_update(USER_ID, f"cadd:{product['id']}"))

    await feed(dp, bot, message_update(USER_ID, t.BTN_CART))
    await feed(dp, bot, message_update(USER_ID, t.BTN_MY_ORDERS))


async def test_russian_session_has_no_uzbek(clean_db):
    db = clean_db
    bot, session, dp = await build()

    session.clear()
    await browse_everything(dp, bot, db, "ru")
    output = collect_output(session)

    leaked = [marker for marker in UZBEK_MARKERS if marker in output]
    assert not leaked, f"Uzbek leaked into a Russian session: {leaked}"


async def test_uzbek_session_has_no_russian(clean_db):
    db = clean_db
    bot, session, dp = await build()

    await feed(dp, bot, message_update(USER_ID, "/start"))
    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))

    session.clear()
    await browse_everything(dp, bot, db, "uz")
    output = collect_output(session)

    leaked = [marker for marker in RUSSIAN_MARKERS if marker in output]
    assert not leaked, f"Russian leaked into an Uzbek session: {leaked}"


async def test_currency_symbol_follows_the_language(clean_db):
    """The base currency's symbol is translated; ₽ and $ are not."""
    db = clean_db
    bot, session, dp = await build()

    ru_symbol = RU.CURRENCY_SYMBOLS[BASE_CURRENCY]
    uz_symbol = UZ.CURRENCY_SYMBOLS[BASE_CURRENCY]

    await feed(dp, bot, message_update(USER_ID, "/start"))
    cat_id = (await db.get_categories("ru"))[0]["id"]

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"cat:{cat_id}"))
    russian_output = collect_output(session)
    assert ru_symbol in russian_output
    assert uz_symbol not in russian_output

    await feed(dp, bot, callback_update(USER_ID, "lng:uz"))
    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"cat:{cat_id}"))
    uzbek_output = collect_output(session)
    assert uz_symbol in uzbek_output
    assert ru_symbol not in uzbek_output


async def test_admin_panel_stays_in_one_language(clean_db):
    db = clean_db
    bot, session, dp = await build()

    await feed(dp, bot, message_update(ADMIN_ID, "/start"))

    session.clear()
    await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_ADMIN))
    await feed(dp, bot, message_update(ADMIN_ID, "/stats"))
    await feed(dp, bot, message_update(ADMIN_ID, RU.BTN_ORDERS))
    output = collect_output(session)

    leaked = [marker for marker in UZBEK_MARKERS if marker in output]
    assert not leaked, f"Uzbek leaked into the Russian admin panel: {leaked}"


async def test_every_demo_item_is_translated(clean_db):
    """Nothing in the seeded catalog may fall back to another language."""
    db = clean_db

    for lang in LOCALES:
        other_langs = [code for code in LOCALES if code != lang]

        for category in await db.get_categories(lang):
            for other in other_langs:
                other_titles = {
                    c["title"] for c in await db.get_categories(other)
                }
                # A category name is allowed to be identical only if it is the
                # same word in both languages; the demo data never is.
                assert category["title"] not in other_titles, (
                    f"category '{category['title']}' is identical in "
                    f"'{lang}' and '{other}' — translation missing"
                )

            products = await db.get_products(category["id"], lang)
            assert products, f"category {category['id']} is empty in '{lang}'"
            for product in products:
                assert product["description"], (
                    f"product {product['id']} has no description in '{lang}'"
                )


async def test_demo_descriptions_differ_between_languages(clean_db):
    db = clean_db

    ru_categories = await db.get_categories("ru")
    uz_categories = await db.get_categories("uz")
    assert len(ru_categories) == len(uz_categories)

    ru_descriptions = []
    uz_descriptions = []
    for category in ru_categories:
        ru_descriptions += [
            p["description"] for p in await db.get_products(category["id"], "ru")
        ]
    for category in uz_categories:
        uz_descriptions += [
            p["description"] for p in await db.get_products(category["id"], "uz")
        ]

    assert ru_descriptions and uz_descriptions
    assert not set(ru_descriptions) & set(uz_descriptions), (
        "some demo descriptions are shared between languages"
    )
