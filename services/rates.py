"""Exchange-rate service.

Rates come from the Central Bank of Uzbekistan and can be overridden by an admin.
A cached copy lives in memory so rendering a price never touches the database.

Failure policy (rule 3.2.6): the API is treated as unreliable. Every call has a
timeout, every error is swallowed, and the last known rates keep working. A bot
that cannot reach cbu.uz still sells — it just shows slightly stale numbers.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from currencies import BASE_CURRENCY, CURRENCIES
from database import db

log = logging.getLogger(__name__)

CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
REQUEST_TIMEOUT = 15          # seconds
REFRESH_INTERVAL = 6 * 60 * 60  # 6 hours
RETRY_INTERVAL = 15 * 60        # after a failure, try again sooner
CACHE_TTL = 300                 # in-memory cache lifetime, seconds

# Rates that ship with the bot so a fresh install can convert before the first
# successful API call. Deliberately rounded — they are a starting point, not truth.
SEED_RATES: dict[str, float] = {
    "USD": 12100.0,
    "RUB": 153.0,
}


class RateProvider:
    """In-memory cache over the `exchange_rates` table."""

    def __init__(self) -> None:
        self._rates: dict[str, float] = {}
        self._loaded_at: float = 0.0
        self._lock = asyncio.Lock()

    def invalidate(self) -> None:
        self._loaded_at = 0.0

    async def all(self) -> dict[str, float]:
        now = time.monotonic()
        if self._rates and now - self._loaded_at < CACHE_TTL:
            return self._rates

        async with self._lock:
            # Another coroutine may have refreshed while we waited.
            if self._rates and time.monotonic() - self._loaded_at < CACHE_TTL:
                return self._rates
            rows = await db.get_rates()
            self._rates = {code: float(row["rate"]) for code, row in rows.items()}
            self._rates[BASE_CURRENCY] = 1.0
            self._loaded_at = time.monotonic()
        return self._rates

    async def get(self, code: str) -> float | None:
        if code == BASE_CURRENCY:
            return 1.0
        return (await self.all()).get(code)


rates = RateProvider()


# ----------------------------------------------------------------- fetching

def parse_cbu(payload: Any) -> dict[str, float]:
    """Turn the CBU payload into {code: base units per one unit}.

    The API reports `Rate` per `Nominal` units, so a currency quoted per 10 units
    has to be divided. Anything we do not sell in is ignored.
    """
    result: dict[str, float] = {}
    if not isinstance(payload, list):
        return result

    wanted = {code for code in CURRENCIES if code != BASE_CURRENCY}

    for entry in payload:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("Ccy", "")).upper()
        if code not in wanted:
            continue
        try:
            rate = float(entry["Rate"])
            nominal = float(entry.get("Nominal", 1) or 1)
        except (KeyError, TypeError, ValueError):
            log.warning("Malformed CBU entry for %s", code)
            continue
        if rate <= 0 or nominal <= 0:
            continue
        result[code] = rate / nominal

    return result


async def fetch_rates() -> dict[str, float]:
    """Ask CBU for the current rates. Returns {} on any failure."""
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CBU_URL) as response:
                if response.status != 200:
                    log.warning("CBU returned HTTP %s", response.status)
                    return {}
                payload = await response.json(content_type=None)
    except asyncio.TimeoutError:
        log.warning("CBU request timed out after %ss", REQUEST_TIMEOUT)
        return {}
    except aiohttp.ClientError as e:
        log.warning("CBU request failed: %s", e)
        return {}
    except Exception as e:  # malformed JSON, DNS failure, ...
        log.warning("CBU request raised %s: %s", type(e).__name__, e)
        return {}

    parsed = parse_cbu(payload)
    if not parsed:
        log.warning("CBU response contained none of the currencies we sell in")
    return parsed


async def refresh_rates() -> int:
    """Fetch and store. Returns how many rates were updated (0 on failure).

    Rates an admin set by hand are left alone — a manual override outranks the
    API until the admin clears it.
    """
    fetched = await fetch_rates()
    if not fetched:
        return 0

    stored = await db.get_rates()
    manual = {code for code, row in stored.items() if row["source"] == "manual"}
    updatable = {code: rate for code, rate in fetched.items() if code not in manual}

    if manual:
        log.info("Keeping manual rates: %s", ", ".join(sorted(manual)))

    count = await db.set_rates_bulk(updatable, source="api")
    rates.invalidate()
    log.info("Rates updated from CBU: %s", count)
    return count


async def ensure_seed_rates() -> None:
    """Give a fresh database something to convert with before the first fetch."""
    stored = await db.get_rates()
    missing = {
        code: rate for code, rate in SEED_RATES.items() if code not in stored
    }
    if missing:
        await db.set_rates_bulk(missing, source="seed")
        rates.invalidate()
        log.info("Seed rates written: %s", ", ".join(sorted(missing)))


# ----------------------------------------------------------------- scheduler

async def rate_refresh_loop(stop: asyncio.Event | None = None) -> None:
    """Background task: refresh on startup, then every REFRESH_INTERVAL."""
    while True:
        try:
            updated = await refresh_rates()
        except Exception as e:  # a crash here must never take the bot down
            log.exception("Rate refresh crashed: %s", e)
            updated = 0

        delay = REFRESH_INTERVAL if updated else RETRY_INTERVAL

        if stop is None:
            await asyncio.sleep(delay)
            continue
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
            return  # stop was set
        except asyncio.TimeoutError:
            continue
