"""SQLite FSM storage: does an unfinished checkout survive a restart?"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from aiogram.fsm.storage.base import StorageKey

from storage import SQLiteStorage

DB = Path(tempfile.gettempdir()) / "shop_bot_fsm_test.db"


@pytest.fixture()
def storage_path() -> Path:
    for suffix in ("", "-journal", "-wal", "-shm"):
        target = Path(str(DB) + suffix)
        if target.exists():
            target.unlink()
    yield DB
    for suffix in ("", "-journal", "-wal", "-shm"):
        target = Path(str(DB) + suffix)
        if target.exists():
            target.unlink()


def _key(user_id: int = 1) -> StorageKey:
    return StorageKey(bot_id=42, chat_id=user_id, user_id=user_id)


async def test_state_round_trip(storage_path):
    storage = SQLiteStorage(str(storage_path))
    key = _key()

    assert await storage.get_state(key) is None

    await storage.set_state(key, "OrderState:name")
    assert await storage.get_state(key) == "OrderState:name"

    await storage.set_state(key, None)
    assert await storage.get_state(key) is None


async def test_data_round_trip(storage_path):
    storage = SQLiteStorage(str(storage_path))
    key = _key()

    assert await storage.get_data(key) == {}

    await storage.set_data(key, {"name": "Tolibjon", "qty": 3})
    assert await storage.get_data(key) == {"name": "Tolibjon", "qty": 3}


async def test_state_and_data_do_not_overwrite_each_other(storage_path):
    """Both live in one row; writing one must not blank the other."""
    storage = SQLiteStorage(str(storage_path))
    key = _key()

    await storage.set_state(key, "OrderState:phone")
    await storage.set_data(key, {"name": "Tolibjon"})

    assert await storage.get_state(key) == "OrderState:phone"
    assert await storage.get_data(key) == {"name": "Tolibjon"}

    await storage.set_state(key, "OrderState:address")
    assert await storage.get_data(key) == {"name": "Tolibjon"}, "data was lost"


async def test_survives_a_restart(storage_path):
    """The whole reason this storage exists."""
    first = SQLiteStorage(str(storage_path))
    key = _key()
    await first.set_state(key, "OrderState:address")
    await first.set_data(key, {"name": "Tolibjon", "phone": "+998901234567"})
    await first.close()

    # A brand-new instance, as after a redeploy.
    second = SQLiteStorage(str(storage_path))
    assert await second.get_state(key) == "OrderState:address"
    assert await second.get_data(key) == {
        "name": "Tolibjon",
        "phone": "+998901234567",
    }


async def test_users_are_isolated(storage_path):
    storage = SQLiteStorage(str(storage_path))

    await storage.set_data(_key(1), {"name": "First"})
    await storage.set_data(_key(2), {"name": "Second"})

    assert await storage.get_data(_key(1)) == {"name": "First"}
    assert await storage.get_data(_key(2)) == {"name": "Second"}


async def test_unicode_is_preserved(storage_path):
    storage = SQLiteStorage(str(storage_path))
    key = _key()

    await storage.set_data(key, {"name": "Тolibjon Бойдуллаев", "addr": "Тошкент"})
    assert (await storage.get_data(key))["addr"] == "Тошкент"


async def test_unserialisable_data_does_not_crash(storage_path):
    """Losing one flow's data beats taking the handler down."""
    storage = SQLiteStorage(str(storage_path))
    key = _key()

    await storage.set_data(key, {"bad": object()})
    assert await storage.get_data(key) == {}


async def test_corrupt_row_is_treated_as_empty(storage_path):
    import aiosqlite

    storage = SQLiteStorage(str(storage_path))
    key = _key()
    await storage.set_data(key, {"ok": 1})

    async with aiosqlite.connect(str(storage_path)) as conn:
        await conn.execute("UPDATE fsm_storage SET data = 'not json'")
        await conn.commit()

    assert await storage.get_data(key) == {}


async def test_clearing_data(storage_path):
    storage = SQLiteStorage(str(storage_path))
    key = _key()

    await storage.set_data(key, {"name": "Tolibjon"})
    await storage.set_data(key, {})
    assert await storage.get_data(key) == {}
