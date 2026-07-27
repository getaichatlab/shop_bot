"""Shared pytest fixtures.

The environment is pinned **before** `config` is imported, and every setting the
bot reads is set explicitly. Without this, `load_dotenv()` would pull in the
developer's own `.env`, so the suite would pass or fail depending on whose
machine it runs on.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_TMP_DB = Path(tempfile.gettempdir()) / "shop_bot_test.db"

# Every variable config.py looks at. Set with os.environ[...] = (not setdefault)
# so a value already present in the shell or in .env cannot leak in.
TEST_ENV = {
    "BOT_TOKEN": "424242:TEST-TOKEN",
    "ADMIN_IDS": "777",
    "ORDERS_CHAT_ID": "",
    "PAYMENT_PROVIDER_TOKEN": "",
    "CURRENCY": "UZS",
    # Empty on purpose: the currency symbol must come from the locale, and a
    # stray override here would mask exactly the bug this suite guards against.
    "CURRENCY_SYMBOL": "",
    "DB_PATH": str(_TMP_DB),
    "REDIS_URL": "",
    "TIMEZONE": "Asia/Tashkent",
    "DEFAULT_LANG": "ru",
    "THROTTLE_RATE": "0",       # rate limiting off in tests
    "LOG_LEVEL": "CRITICAL",
    "LOG_DIR": tempfile.gettempdir(),
    "USE_WEBHOOK": "false",
    "WEBHOOK_BASE_URL": "",
    "WEBHOOK_SECRET": "",
    "WEBHOOK_PATH": "",
    "PORT": "8080",
}

os.environ.update(TEST_ENV)

ADMIN_ID = int(TEST_ENV["ADMIN_IDS"])
USER_ID = 111


def test_environment_is_hermetic() -> None:
    """Guards the guard: a leaked .env value would silently weaken every test."""
    from config import settings

    assert settings.payment.currency_symbol == "", (
        "CURRENCY_SYMBOL leaked from the environment — the locale must decide "
        "the symbol during tests"
    )
    assert settings.default_lang == "ru"
    assert settings.bot.admin_ids == [ADMIN_ID]
    assert settings.db_path == str(_TMP_DB)


@pytest.fixture()
def db_path() -> Path:
    return _TMP_DB


@pytest.fixture()
async def clean_db(db_path: Path):
    """Fresh database seeded with the demo catalog for every test.

    The exchange-rate cache is a module-level singleton, so it has to be cleared
    too — otherwise a rate written by one test would still be served to the next
    one after its database was deleted.
    """
    for suffix in ("", "-journal", "-wal", "-shm"):
        target = Path(str(db_path) + suffix)
        if target.exists():
            target.unlink()

    from database import queries
    from services.rates import rates

    rates.invalidate()
    await queries.init_db()
    yield queries
    rates.invalidate()

    for suffix in ("", "-journal", "-wal", "-shm"):
        target = Path(str(db_path) + suffix)
        if target.exists():
            target.unlink()
