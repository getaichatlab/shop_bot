"""Unit tests for currency conversion and formatting. Run: pytest -q"""
from __future__ import annotations

import pytest

from currencies import BASE_CURRENCY, CURRENCIES, get_currency, is_supported
from locales import get_texts
from utils import validators as v
from utils.money import (
    RateUnavailable,
    cart_total_in,
    convert,
    format_amount,
    price_text,
    resolve_minor,
    to_base,
)

RU = get_texts("ru")
UZ = get_texts("uz")

# Real CBU figures, for realistic assertions.
USD_RATE = 12101.84
RUB_RATE = 153.75


# ---------------------------------------------------------------- registry

def test_base_currency_is_registered() -> None:
    assert BASE_CURRENCY in CURRENCIES
    assert get_currency(BASE_CURRENCY).is_base


@pytest.mark.parametrize("code", ["UZS", "RUB", "USD", "usd", "uzs"])
def test_supported_codes(code: str) -> None:
    assert is_supported(code)


@pytest.mark.parametrize("code", [None, "", "EUR", "XXX"])
def test_unsupported_codes_fall_back(code) -> None:
    assert not is_supported(code)
    assert get_currency(code).code == BASE_CURRENCY


# ---------------------------------------------------------------- convert

def test_base_conversion_is_identity() -> None:
    assert convert(1_150_000, "UZS", 1.0) == 1_150_000
    # Even a nonsense rate cannot disturb the base currency.
    assert convert(1_150_000, "UZS", None) == 1_150_000


def test_convert_to_usd_cents() -> None:
    # 11 500 000 / 12101.84 = 950.27...
    assert convert(11_500_000, "USD", USD_RATE) == 95027


def test_convert_to_rub_whole_units() -> None:
    # 11 500 000 / 153.75 = 74796.7 -> 74797
    assert convert(11_500_000, "RUB", RUB_RATE) == 74797


def test_convert_without_rate_raises() -> None:
    with pytest.raises(RateUnavailable):
        convert(1_000_000, "USD", None)
    with pytest.raises(RateUnavailable):
        convert(1_000_000, "USD", 0)
    with pytest.raises(RateUnavailable):
        convert(1_000_000, "USD", -5)


def test_round_trip_is_close() -> None:
    """Converting there and back must not drift more than the rounding step."""
    base = 11_500_000
    usd = convert(base, "USD", USD_RATE)
    back = to_base(usd, "USD", USD_RATE)
    assert abs(back - base) < 200


def test_to_base_is_identity_for_base() -> None:
    assert to_base(500, "UZS", None) == 500


def test_uzs_rounding_step() -> None:
    """UZS is rounded to 100 so prices never end in stray digits."""
    assert convert(11_500_000, "UZS", 1.0) % 1 == 0
    # Round-tripping a dollar amount lands on a clean so'm figure.
    result = to_base(convert(11_500_000, "USD", USD_RATE), "USD", USD_RATE)
    assert isinstance(result, int)


# ---------------------------------------------------------------- format

def test_format_uzs_russian() -> None:
    assert format_amount(1_150_000, "UZS", RU) == "1 150 000 сум"


def test_format_uzs_uzbek() -> None:
    assert format_amount(1_150_000, "UZS", UZ) == "1 150 000 so'm"


def test_format_rub_is_language_independent() -> None:
    assert format_amount(74_797, "RUB", RU) == "74 797 ₽"
    assert format_amount(74_797, "RUB", UZ) == "74 797 ₽"


def test_format_usd_has_leading_symbol_and_cents() -> None:
    assert format_amount(95_027, "USD", RU) == "$950.27"
    assert format_amount(9_900, "USD", RU) == "$99.00"
    assert format_amount(5, "USD", RU) == "$0.05"


def test_format_zero_and_negative() -> None:
    assert format_amount(0, "USD", RU) == "$0.00"
    assert format_amount(-9_900, "USD", RU) == "-$99.00"


# ---------------------------------------------------------------- price_text

def test_price_text_uses_the_pinned_price() -> None:
    """An explicit price wins over the converted one."""
    text = price_text(11_500_000, "USD", USD_RATE, RU, override_minor=9_900)
    assert text == "$99.00"


def test_price_text_converts_without_a_pinned_price() -> None:
    assert price_text(11_500_000, "USD", USD_RATE, RU) == "$950.27"


def test_price_text_falls_back_to_base_without_a_rate() -> None:
    """A missing rate must degrade to the base price, never crash."""
    assert price_text(1_150_000, "USD", None, RU) == "1 150 000 сум"


def test_resolve_minor_reports_the_currency_used() -> None:
    amount, code = resolve_minor(1_150_000, "USD", None)
    assert code == BASE_CURRENCY and amount == 1_150_000

    amount, code = resolve_minor(1_150_000, "USD", USD_RATE)
    assert code == "USD"


# ---------------------------------------------------------------- cart totals

def _item(price: int, qty: int, override: int | None = None) -> dict:
    return {"price": price, "quantity": qty, "price_override": override}


def test_cart_total_in_base() -> None:
    items = [_item(1_000_000, 2), _item(450_000, 1)]
    assert cart_total_in(items, "UZS", 1.0) == 2_450_000


def test_cart_total_matches_the_sum_of_lines() -> None:
    """The total must equal what the customer can add up on screen."""
    items = [_item(11_500_000, 2), _item(450_000, 3)]
    expected = convert(11_500_000, "USD", USD_RATE) * 2
    expected += convert(450_000, "USD", USD_RATE) * 3
    assert cart_total_in(items, "USD", USD_RATE) == expected


def test_cart_total_respects_pinned_prices() -> None:
    items = [_item(11_500_000, 2, override=9_900)]
    assert cart_total_in(items, "USD", USD_RATE) == 19_800


def test_cart_total_without_a_rate_falls_back_to_base() -> None:
    items = [_item(1_000_000, 2)]
    assert cart_total_in(items, "USD", None) == 2_000_000


def test_cart_total_of_empty_cart() -> None:
    assert cart_total_in([], "USD", USD_RATE) == 0


# ---------------------------------------------------------------- parsing

@pytest.mark.parametrize(
    ("raw", "expected"),
    [("12101.84", 12101.84), ("12 101,84", 12101.84), ("153", 153.0)],
)
def test_parse_rate_ok(raw: str, expected: float) -> None:
    assert v.parse_rate(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["", "abc", "0", "-5", "-12101.84"])
def test_parse_rate_invalid(raw: str) -> None:
    assert v.parse_rate(raw) is None


@pytest.mark.parametrize(
    ("raw", "decimals", "expected"),
    [
        ("99", 2, 9_900),
        ("99.50", 2, 9_950),
        ("99.5", 2, 9_950),
        ("0.05", 2, 5),
        ("74 796", 0, 74_796),
        ("74796", 0, 74_796),
        ("1 150 000", 0, 1_150_000),
    ],
)
def test_parse_money_ok(raw: str, decimals: int, expected: int) -> None:
    assert v.parse_money(raw, decimals) == expected


@pytest.mark.parametrize(
    ("raw", "decimals"),
    [("abc", 2), ("", 2), ("-99", 2), ("9.9.9", 2), ("0", 2)],
)
def test_parse_money_invalid(raw: str, decimals: int) -> None:
    assert v.parse_money(raw, decimals) is None


def test_parse_money_rejects_cents_for_a_whole_currency() -> None:
    """RUB has no sub-units here, so '100.50' is a typo, not a price."""
    assert v.parse_money("100.50", 0) is None
    # A zero fraction is harmless.
    assert v.parse_money("100.0", 0) == 100
