"""Telegram Stars pricing.

Stars are Telegram's own unit for digital goods. They need no merchant account
and no provider token, which makes them the only payment method a portfolio demo
can actually let a stranger complete end to end.

Conversion path: base currency -> USD (via the stored rate) -> Stars (via the
retail price of one Star). Both steps are configurable, and the result is a
whole number of Stars, rounded up so the shop is never underpaid.
"""
from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

MIN_STARS = 1
# Telegram rejects invoices above this; well beyond any sane order.
MAX_STARS = 2_500_000


def stars_for(base_amount: int, usd_rate: float | None, star_price_usd: float) -> int | None:
    """Stars needed to cover `base_amount` of the base currency.

    Returns None when the amount cannot be priced — a missing USD rate or a
    nonsensical Star price. Callers must handle that instead of charging a
    number they cannot justify.
    """
    if base_amount <= 0:
        return None
    if not usd_rate or usd_rate <= 0:
        return None
    if not star_price_usd or star_price_usd <= 0:
        return None

    usd = Decimal(base_amount) / Decimal(str(usd_rate))
    stars = usd / Decimal(str(star_price_usd))

    # Round up: charging 0.4 Stars is impossible, and rounding down would sell
    # at a loss on every single order.
    value = int(stars.to_integral_value(rounding=ROUND_CEILING))
    return max(MIN_STARS, min(value, MAX_STARS))
