"""Exchange-rate service: parsing, failure handling, manual overrides."""
from __future__ import annotations

import pytest

import services.rates as rates_module
from services.rates import RateProvider, parse_cbu, refresh_rates

# A trimmed copy of a real cbu.uz response, including currencies we do not sell in
# and one quoted per 10 units.
CBU_SAMPLE = [
    {"Ccy": "USD", "Nominal": "1", "Rate": "12101.84", "Date": "24.07.2026"},
    {"Ccy": "RUB", "Nominal": "1", "Rate": "153.75", "Date": "24.07.2026"},
    {"Ccy": "EUR", "Nominal": "1", "Rate": "13811.83", "Date": "24.07.2026"},
    {"Ccy": "IDR", "Nominal": "10", "Rate": "6.76", "Date": "24.07.2026"},
]


# ---------------------------------------------------------------- parsing

def test_parse_keeps_only_currencies_we_sell_in() -> None:
    parsed = parse_cbu(CBU_SAMPLE)
    assert set(parsed) == {"USD", "RUB"}


def test_parse_reads_the_rate() -> None:
    parsed = parse_cbu(CBU_SAMPLE)
    assert parsed["USD"] == pytest.approx(12101.84)
    assert parsed["RUB"] == pytest.approx(153.75)


def test_parse_divides_by_nominal() -> None:
    """A currency quoted per 10 units must be normalised to one unit."""
    payload = [{"Ccy": "USD", "Nominal": "10", "Rate": "121018.4"}]
    assert parse_cbu(payload)["USD"] == pytest.approx(12101.84)


def test_parse_never_returns_the_base_currency() -> None:
    payload = [{"Ccy": "UZS", "Nominal": "1", "Rate": "1"}]
    assert parse_cbu(payload) == {}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        "not a list",
        [],
        [{"Ccy": "USD"}],                               # no Rate
        [{"Ccy": "USD", "Rate": "abc"}],                # unparsable
        [{"Ccy": "USD", "Rate": "0", "Nominal": "1"}],  # nonsense
        [{"Ccy": "USD", "Rate": "-5", "Nominal": "1"}],
        [{"Ccy": "USD", "Rate": "10", "Nominal": "0"}],
        ["junk", 42],
    ],
)
def test_parse_survives_malformed_payloads(payload) -> None:
    assert parse_cbu(payload) == {}


# ---------------------------------------------------------------- refresh

async def test_refresh_stores_rates(clean_db, monkeypatch) -> None:
    db = clean_db

    async def fake_fetch():
        return {"USD": 12101.84, "RUB": 153.75}

    monkeypatch.setattr(rates_module, "fetch_rates", fake_fetch)

    count = await refresh_rates()
    assert count == 2
    assert await db.get_rate("USD") == pytest.approx(12101.84)


async def test_refresh_failure_keeps_old_rates(clean_db, monkeypatch) -> None:
    """A dead API must never wipe what we already know."""
    db = clean_db
    await db.set_rate("USD", 12000.0, source="api")

    async def failing_fetch():
        return {}

    monkeypatch.setattr(rates_module, "fetch_rates", failing_fetch)

    count = await refresh_rates()
    assert count == 0
    assert await db.get_rate("USD") == pytest.approx(12000.0)


async def test_manual_rate_survives_an_api_refresh(clean_db, monkeypatch) -> None:
    """An admin's number outranks the central bank until they clear it."""
    db = clean_db
    await db.set_rate("USD", 13000.0, source="manual")
    await db.set_rate("RUB", 150.0, source="api")

    async def fake_fetch():
        return {"USD": 12101.84, "RUB": 153.75}

    monkeypatch.setattr(rates_module, "fetch_rates", fake_fetch)

    await refresh_rates()

    assert await db.get_rate("USD") == pytest.approx(13000.0), "manual overwritten"
    assert await db.get_rate("RUB") == pytest.approx(153.75), "api rate not refreshed"


async def test_seed_rates_only_fill_gaps(clean_db) -> None:
    db = clean_db
    await db.set_rate("USD", 13000.0, source="manual")

    await rates_module.ensure_seed_rates()

    assert await db.get_rate("USD") == pytest.approx(13000.0)
    assert await db.get_rate("RUB") is not None


# ---------------------------------------------------------------- provider

async def test_provider_returns_one_for_the_base_currency(clean_db) -> None:
    provider = RateProvider()
    assert await provider.get("UZS") == 1.0


async def test_provider_caches_and_invalidates(clean_db) -> None:
    db = clean_db
    provider = RateProvider()

    await db.set_rate("USD", 12000.0)
    assert await provider.get("USD") == pytest.approx(12000.0)

    # Written behind the cache's back: the old value must still be served.
    await db.set_rate("USD", 13000.0)
    assert await provider.get("USD") == pytest.approx(12000.0)

    provider.invalidate()
    assert await provider.get("USD") == pytest.approx(13000.0)


async def test_provider_returns_none_for_an_unknown_rate(clean_db) -> None:
    provider = RateProvider()
    assert await provider.get("USD") is None


async def test_fetch_rates_swallows_network_errors(monkeypatch) -> None:
    """Any exception from aiohttp must become an empty result, not a crash."""
    import aiohttp

    class ExplodingSession:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            raise aiohttp.ClientError("boom")

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(aiohttp, "ClientSession", ExplodingSession)
    assert await rates_module.fetch_rates() == {}
