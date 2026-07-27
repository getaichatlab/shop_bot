"""Conversion and formatting of money.

Pure functions — no I/O, fully unit-tested. Rates are passed in, never fetched
here, so the same code runs identically in tests and in production.

A rate is expressed as **base-currency units per one unit of the currency**:
with UZS as base, `USD -> 12101.84` means one dollar costs 12 101.84 so'm.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from types import ModuleType

from currencies import BASE_CURRENCY, Currency, get_currency


class RateUnavailable(Exception):
    """No usable rate for the requested currency."""


def convert(base_amount: int, code: str, rate: float | None) -> int:
    """Convert an amount in the base currency to minor units of `code`.

    `base_amount` is in base-currency minor units (so'm).
    Returns minor units of the target currency (cents for USD).
    """
    currency = get_currency(code)
    if currency.is_base:
        return base_amount

    if not rate or rate <= 0:
        raise RateUnavailable(f"no rate for {code}")

    # Decimal keeps the rounding exact and predictable; float would drift.
    value = (Decimal(base_amount) / Decimal(str(rate))) * currency.factor
    minor = int(value.to_integral_value(rounding=ROUND_HALF_UP))
    return _round_step(minor, currency)


def to_base(amount_minor: int, code: str, rate: float | None) -> int:
    """Inverse of `convert`: minor units of `code` back to base minor units."""
    currency = get_currency(code)
    if currency.is_base:
        return amount_minor

    if not rate or rate <= 0:
        raise RateUnavailable(f"no rate for {code}")

    value = (Decimal(amount_minor) / currency.factor) * Decimal(str(rate))
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def _round_step(minor: int, currency: Currency) -> int:
    """Round to the currency's display step so prices look deliberate."""
    step = currency.rounding_step
    if step <= 1:
        return minor
    return int(Decimal(minor / step).to_integral_value(rounding=ROUND_HALF_UP)) * step


def format_amount(amount_minor: int, code: str, t: ModuleType) -> str:
    """'1 150 000 so'm', '74 796 ₽', '$950.27' — symbol taken from the locale."""
    currency = get_currency(code)
    symbol = t.CURRENCY_SYMBOLS.get(currency.code, currency.code)

    if currency.decimals:
        whole, frac = divmod(abs(amount_minor), currency.factor)
        body = f"{whole:,}".replace(",", " ") + "." + str(frac).zfill(currency.decimals)
    else:
        body = f"{abs(amount_minor):,}".replace(",", " ")

    sign = "-" if amount_minor < 0 else ""

    # A leading symbol reads naturally for USD, a trailing one for so'm and ₽.
    if currency.code == "USD":
        return f"{sign}{symbol}{body}"
    return f"{sign}{body} {symbol}"


def price_text(
    base_amount: int,
    code: str,
    rate: float | None,
    t: ModuleType,
    override_minor: int | None = None,
) -> str:
    """Render a price, preferring an explicit per-currency price.

    `override_minor` is the price the admin typed for this currency. When it is
    missing the amount is converted from the base currency using `rate`; when
    the rate is missing too, the base price is shown instead of failing.
    """
    if override_minor is not None:
        return format_amount(override_minor, code, t)

    try:
        return format_amount(convert(base_amount, code, rate), code, t)
    except RateUnavailable:
        return format_amount(base_amount, BASE_CURRENCY, t)


def cart_total_in(
    items: list[dict], code: str, rate: float | None
) -> int:
    """Total of a cart in the display currency.

    Each line is converted (or taken from its pinned price) *before* summing, so
    the total always equals what the customer read line by line. Summing in the
    base currency and converting once would drift by a few units.
    """
    total = 0
    for item in items:
        override = item.get("price_override")
        quantity = item["quantity"]
        if override is not None:
            total += override * quantity
        else:
            try:
                total += convert(item["price"], code, rate) * quantity
            except RateUnavailable:
                total += item["price"] * quantity
    return total


def resolve_minor(
    base_amount: int,
    code: str,
    rate: float | None,
    override_minor: int | None = None,
) -> tuple[int, str]:
    """The numeric counterpart of `price_text`.

    Returns (amount in minor units, the currency actually used) so callers can
    tell when a display fell back to the base currency.
    """
    if override_minor is not None:
        return override_minor, get_currency(code).code
    try:
        return convert(base_amount, code, rate), get_currency(code).code
    except RateUnavailable:
        return base_amount, BASE_CURRENCY
