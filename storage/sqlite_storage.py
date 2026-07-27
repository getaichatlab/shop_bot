"""FSM storage backed by the same SQLite file as the rest of the bot.

Why this exists: aiogram ships MemoryStorage (lost on restart) and RedisStorage
(needs a Redis server). Free hosting rarely gives you Redis, and losing a
half-finished checkout every time the app redeploys is a real, visible bug for a
customer who has already typed their name and phone number.

This storage keeps state in a table next to the orders, so it survives a restart
with no extra infrastructure. It is not built for high concurrency — for that,
use Redis — but for a shop bot it is the right trade.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import aiosqlite
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS fsm_storage (
    key        TEXT PRIMARY KEY,
    state      TEXT,
    data       TEXT NOT NULL DEFAULT '{}',
    updated_at REAL NOT NULL
);
"""

# Abandoned flows are swept so the table cannot grow without bound.
TTL_SECONDS = 7 * 24 * 60 * 60
CLEANUP_EVERY = 500


class SQLiteStorage(BaseStorage):
    """Persistent FSM storage with no external dependency."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ready = False
        self._writes = 0

    # -- lifecycle -------------------------------------------------------

    async def _ensure_schema(self) -> None:
        if self._ready:
            return
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(SCHEMA)
            await conn.commit()
        self._ready = True

    @staticmethod
    def _key(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"

    async def _maybe_cleanup(self, conn: aiosqlite.Connection) -> None:
        self._writes += 1
        if self._writes % CLEANUP_EVERY:
            return
        cutoff = time.time() - TTL_SECONDS
        await conn.execute("DELETE FROM fsm_storage WHERE updated_at < ?", (cutoff,))

    async def _upsert(self, key: str, **fields: Any) -> None:
        await self._ensure_schema()
        assignments = ", ".join(f"{name} = ?" for name in fields)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                f"""
                INSERT INTO fsm_storage (key, state, data, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET {assignments}, updated_at = ?
                """,
                (
                    key,
                    fields.get("state"),
                    fields.get("data", "{}"),
                    time.time(),
                    *fields.values(),
                    time.time(),
                ),
            )
            await self._maybe_cleanup(conn)
            await conn.commit()

    # -- BaseStorage API -------------------------------------------------

    async def set_state(self, key: StorageKey, state: State | str | None = None) -> None:
        value = state.state if isinstance(state, State) else state
        await self._upsert(self._key(key), state=value)

    async def get_state(self, key: StorageKey) -> str | None:
        await self._ensure_schema()
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                "SELECT state FROM fsm_storage WHERE key = ?", (self._key(key),)
            )
            row = await cur.fetchone()
        return row[0] if row else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        try:
            payload = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # Better to lose one flow's data than to crash the handler.
            log.error("FSM data is not JSON-serialisable, storing empty: %s", e)
            payload = "{}"
        await self._upsert(self._key(key), data=payload)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        await self._ensure_schema()
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                "SELECT data FROM fsm_storage WHERE key = ?", (self._key(key),)
            )
            row = await cur.fetchone()

        if not row or not row[0]:
            return {}
        try:
            value = json.loads(row[0])
        except json.JSONDecodeError:
            log.warning("Corrupt FSM data for %s, resetting", self._key(key))
            return {}
        return value if isinstance(value, dict) else {}

    async def close(self) -> None:
        return None
