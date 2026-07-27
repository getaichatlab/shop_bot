"""Pure input validators. No I/O — fully unit-testable (see tests/)."""
from __future__ import annotations

import re

# Telegram limits
MAX_MESSAGE_LEN = 4096
MAX_CAPTION_LEN = 1024

# Field limits
NAME_MIN, NAME_MAX = 3, 100
ADDRESS_MIN, ADDRESS_MAX = 5, 300
COMMENT_MAX = 500
TITLE_MAX = 120
DESCRIPTION_MAX = 800
PRICE_MIN, PRICE_MAX = 1, 10_000_000_000

_PHONE_RE = re.compile(r"^\+?\d{9,15}$")
_DIGITS_ONLY = re.compile(r"[^\d]")


def normalize_phone(raw: str) -> str:
    """Strip separators so '+998 90 123-45-67' becomes '+998901234567'."""
    cleaned = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    return cleaned


def is_valid_phone(raw: str) -> bool:
    return bool(_PHONE_RE.match(normalize_phone(raw)))


def validate_name(raw: str) -> tuple[bool, str]:
    """Returns (ok, cleaned_or_reason). Reason is a key, not a user message."""
    value = " ".join(raw.split())
    if len(value) < NAME_MIN:
        return False, "short"
    if len(value) > NAME_MAX:
        return False, "long"
    return True, value


def validate_address(raw: str) -> tuple[bool, str]:
    value = " ".join(raw.split())
    if len(value) < ADDRESS_MIN:
        return False, "short"
    if len(value) > ADDRESS_MAX:
        return False, "long"
    return True, value


def validate_comment(raw: str) -> tuple[bool, str]:
    value = " ".join(raw.split())
    if len(value) > COMMENT_MAX:
        return False, "long"
    return True, value


def validate_title(raw: str) -> tuple[bool, str]:
    value = " ".join(raw.split())
    if not value:
        return False, "short"
    if len(value) > TITLE_MAX:
        return False, "long"
    return True, value


def validate_description(raw: str) -> tuple[bool, str]:
    value = " ".join(raw.split())
    if len(value) > DESCRIPTION_MAX:
        return False, "long"
    return True, value


def parse_price(raw: str) -> int | None:
    """'1 150 000' / '1,150,000' -> 1150000. Returns None if invalid.

    Negative input is rejected outright: stripping the separators would
    otherwise silently turn '-500' into 500.
    """
    if raw is None:
        return None
    text = raw.strip()
    if text.startswith(("-", "−")):
        return None
    cleaned = _DIGITS_ONLY.sub("", text)
    if not cleaned:
        return None
    try:
        value = int(cleaned)
    except ValueError:
        return None
    if not (PRICE_MIN <= value <= PRICE_MAX):
        return None
    return value


def parse_rate(raw: str) -> float | None:
    """'12101.84' / '12 101,84' -> 12101.84. Rejects zero and negatives."""
    if raw is None:
        return None
    text = raw.strip().replace(" ", "").replace(",", ".")
    if text.startswith(("-", "−")):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value <= 0 or value > 1_000_000_000:
        return None
    return value


def parse_money(raw: str, decimals: int) -> int | None:
    """Parse a typed price into minor units of a currency.

    '99'      with decimals=2 -> 9900
    '99.50'   with decimals=2 -> 9950
    '74 796'  with decimals=0 -> 74796
    """
    if raw is None:
        return None
    text = raw.strip().replace(" ", "").replace(",", ".")
    if text.startswith(("-", "−")):
        return None
    if not text:
        return None

    if text.count(".") > 1:
        return None
    whole, _, frac = text.partition(".")
    if not whole.isdigit() or (frac and not frac.isdigit()):
        return None

    if decimals == 0:
        if frac and int(frac) != 0:
            return None  # this currency has no sub-units
        value = int(whole)
    else:
        frac = (frac + "0" * decimals)[:decimals]
        value = int(whole) * (10 ** decimals) + int(frac)

    if not (PRICE_MIN <= value <= PRICE_MAX):
        return None
    return value


def parse_positive_int(raw: str) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw.isdigit():
        return None
    value = int(raw)
    return value if value > 0 else None
