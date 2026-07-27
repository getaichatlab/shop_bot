"""Guards that matter because this repository and this bot are public.

Two audiences to protect: a stranger poking at the deployed demo, and anyone
reading the source on GitHub.
"""
from __future__ import annotations

import re
from pathlib import Path

from locales import get_texts
from payments import PROVIDERS
from tests.conftest import USER_ID
from tests.mocks import callback_update, contact_update, message_update
from tests.test_flow import build, feed, head

RU = get_texts("ru")
SKIP_WORD = "нет"
ROOT = Path(__file__).resolve().parents[1]

# Files git would actually publish.
TRACKED_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".txt", ".sql", ".example", ".sh"}
SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "logs", ".pytest_cache"}


def published_files() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == ".env":
            continue
        if path.suffix in TRACKED_SUFFIXES or path.name in {
            "Dockerfile",
            "Procfile",
            ".gitignore",
            ".env.example",
        }:
            out.append(path)
    return out


# ---------------------------------------------------------------- repo hygiene

def test_no_bot_token_is_committed() -> None:
    """A Telegram token is `digits:AA…`. The .env.example placeholder is not."""
    pattern = re.compile(r"[0-9]{9,10}:AA[A-Za-z0-9_-]{32,}")
    offenders = []
    for path in published_files():
        if path.name == ".env.example":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"a bot token appears in: {offenders}"


def test_gitignore_covers_the_dangerous_paths() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in (".env", "*.db", "logs/", "backups/"):
        assert entry in ignored, f".gitignore is missing {entry}"


def test_no_env_file_would_be_published() -> None:
    assert not any(p.name == ".env" for p in published_files())


def test_demo_requisites_are_impossible_numbers() -> None:
    """A public demo must never display something that looks like a real card."""
    for code in ("card_uz", "sber"):
        card = PROVIDERS[code].requisites()[0]
        digits = re.sub(r"\D", "", card)
        assert set(digits) == {"0"}, f"{code} ships a plausible card number: {card}"

    phone = PROVIDERS["sbp"].requisites()[0]
    assert set(re.sub(r"\D", "", phone)) == {"0"}, f"sbp ships a plausible phone: {phone}"

    for code in ("card_uz", "sbp", "sber"):
        holder = PROVIDERS[code].requisites()[1]
        assert "DEMO" in holder.upper(), f"{code} holder is not marked as a demo"


def test_no_personal_name_in_shipped_requisites() -> None:
    joined = " ".join(
        value for code in ("card_uz", "sbp", "sber") for value in PROVIDERS[code].requisites()
    )
    for marker in ("Tolibjon", "Толибжон", "Boydullayev", "Бойдуллаев"):
        assert marker not in joined, f"a personal name ships in the requisites: {marker}"


def test_security_policy_exists() -> None:
    assert (ROOT / "SECURITY.md").exists()


def test_ci_workflow_exists() -> None:
    workflow = ROOT / ".github" / "workflows" / "tests.yml"
    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "pytest" in text
    assert "token" in text.lower(), "CI should also scan for a committed token"


# ---------------------------------------------------------------- runtime

async def _order(dp, bot, db, index: int = 0) -> int:
    cat_id = (await db.get_categories("ru"))[0]["id"]
    products = await db.get_products(cat_id, "ru")
    product = products[index % len(products)]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{product['id']}"))

    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))
    if await db.get_profile(USER_ID) is None:
        await feed(dp, bot, message_update(USER_ID, "Tolibjon Boydullayev"))
        await feed(dp, bot, contact_update(USER_ID, "+998901234567"))
    await feed(dp, bot, message_update(USER_ID, "Toshkent, Amir Temur 12"))
    await feed(dp, bot, message_update(USER_ID, SKIP_WORD))
    await feed(dp, bot, callback_update(USER_ID, "ord:confirm"))
    return len(await db.get_user_orders(USER_ID, limit=100))


async def test_a_transfer_screen_warns_that_it_is_a_demo(clean_db):
    """Nobody should send money to a placeholder card because of this bot."""
    from config import settings

    assert settings.payment.is_demo, "tests should run in demo mode"

    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))
    await _order(dp, bot, db)
    order_id = (await db.get_user_orders(USER_ID))[0]["id"]

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, f"pay:{order_id}:card_uz"))

    said = " ".join(session.texts())
    assert head(RU.PAY_MANUAL_DEMO_WARNING.strip()) in said
    assert "не переводите" in said.lower()


async def test_open_orders_are_capped(clean_db, monkeypatch):
    """A public bot must not let one account fill the database by clicking."""
    import dataclasses

    from config import settings
    import handlers.order as order_module

    patched = dataclasses.replace(settings, max_open_orders=3)
    monkeypatch.setattr(order_module, "settings", patched)

    db = clean_db
    bot, session, dp = await build()
    monkeypatch.setattr(order_module, "settings", patched)
    await feed(dp, bot, message_update(USER_ID, "/start"))

    for index in range(3):
        await _order(dp, bot, db, index)
    assert len(await db.get_user_orders(USER_ID, limit=100)) == 3

    # The fourth attempt is refused before anything is written.
    cat_id = (await db.get_categories("ru"))[0]["id"]
    product = (await db.get_products(cat_id, "ru"))[0]
    await feed(dp, bot, callback_update(USER_ID, f"cadd:{product['id']}"))

    session.clear()
    await feed(dp, bot, callback_update(USER_ID, "nav:checkout"))

    answers = session.calls_of("AnswerCallbackQuery")
    assert answers, "the callback must be answered"
    assert head(RU.ORDER_TOO_MANY_OPEN) in str(answers[-1].data.get("text", ""))
    assert len(await db.get_user_orders(USER_ID, limit=100)) == 3, "an order slipped through"


async def test_a_closed_order_frees_a_slot(clean_db, monkeypatch):
    """The cap counts unfinished orders, not lifetime orders."""
    import dataclasses

    from config import settings
    import handlers.order as order_module

    patched = dataclasses.replace(settings, max_open_orders=1)
    monkeypatch.setattr(order_module, "settings", patched)

    db = clean_db
    bot, session, dp = await build()
    monkeypatch.setattr(order_module, "settings", patched)
    await feed(dp, bot, message_update(USER_ID, "/start"))

    await _order(dp, bot, db)
    first = (await db.get_user_orders(USER_ID))[0]["id"]
    await db.set_order_status(first, "done")

    count = await _order(dp, bot, db, 1)
    assert count == 2, "closing an order should free a slot"


async def test_a_stranger_cannot_reach_the_admin_panel(clean_db):
    db = clean_db
    bot, session, dp = await build()
    await feed(dp, bot, message_update(USER_ID, "/start"))

    session.clear()
    for probe in (RU.BTN_ADMIN, "/stats", "/rates", RU.BTN_BROADCAST, RU.BTN_RATES):
        await feed(dp, bot, message_update(USER_ID, probe))

    said = " ".join(session.texts())
    assert RU.ADMIN_PANEL not in said
    assert head(RU.ADMIN_STATS) not in said
    assert head(RU.ADMIN_RATES_HEADER) not in said
