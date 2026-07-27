"""Currency registry.

Money is stored and passed around as an integer number of **minor units** of a
currency — so'm for UZS, rubles for RUB, cents for USD. Floats are never used to
hold an amount; they appear only inside a single conversion step.

`BASE_CURRENCY` is the accounting currency: product prices, order totals and the
payment invoice all live in it. Every other currency is a display layer on top.
"""
from __future__ import annotations

from dataclasses import dataclass

BASE_CURRENCY = "UZS"


@dataclass(frozen=True)
class Currency:
    code: str
    decimals: int          # digits after the separator shown to the user
    # Converted values are rounded to this many minor units, so a price reads
    # 950 000 so'm rather than 949 837 so'm.
    rounding_step: int = 1

    @property
    def factor(self) -> int:
        return 10 ** self.decimals

    @property
    def is_base(self) -> bool:
        return self.code == BASE_CURRENCY


CURRENCIES: dict[str, Currency] = {
    "UZS": Currency(code="UZS", decimals=0, rounding_step=100),
    "RUB": Currency(code="RUB", decimals=0, rounding_step=1),
    "USD": Currency(code="USD", decimals=2, rounding_step=1),
}

# Order shown in the currency picker.
CURRENCY_ORDER: tuple[str, ...] = ("UZS", "RUB", "USD")


def get_currency(code: str | None) -> Currency:
    return CURRENCIES.get((code or "").upper(), CURRENCIES[BASE_CURRENCY])


def is_supported(code: str | None) -> bool:
    return (code or "").upper() in CURRENCIES


__all__ = [
    "BASE_CURRENCY",
    "CURRENCIES",
    "CURRENCY_ORDER",
    "Currency",
    "get_currency",
    "is_supported",
]
