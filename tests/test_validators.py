"""Unit tests for pure logic (rule 3.11). Run: pytest -q"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import validators as v  # noqa: E402


# ----------------------------------------------------------------- phone

@pytest.mark.parametrize(
    "raw",
    [
        "+998901234567",
        "998901234567",
        "+998 90 123 45 67",
        "+998-90-123-45-67",
        "(998)901234567",
    ],
)
def test_valid_phones(raw: str) -> None:
    assert v.is_valid_phone(raw) is True


@pytest.mark.parametrize(
    "raw",
    ["", "abc", "12345", "+998abc123456", "++998901234567", "9" * 20],
)
def test_invalid_phones(raw: str) -> None:
    assert v.is_valid_phone(raw) is False


def test_normalize_phone_strips_separators() -> None:
    assert v.normalize_phone("+998 90 123-45-67") == "+998901234567"


# ----------------------------------------------------------------- name

def test_name_too_short() -> None:
    ok, reason = v.validate_name("Ab")
    assert ok is False and reason == "short"


def test_name_too_long() -> None:
    ok, reason = v.validate_name("A" * (v.NAME_MAX + 1))
    assert ok is False and reason == "long"


def test_name_collapses_whitespace() -> None:
    ok, value = v.validate_name("  Tolibjon   Boydullayev  ")
    assert ok is True
    assert value == "Tolibjon Boydullayev"


# ----------------------------------------------------------------- address

def test_address_too_short() -> None:
    ok, reason = v.validate_address("abc")
    assert ok is False and reason == "short"


def test_address_ok() -> None:
    ok, value = v.validate_address("Toshkent, Amir Temur 12, 45-xonadon")
    assert ok is True
    assert value.startswith("Toshkent")


def test_address_too_long() -> None:
    ok, reason = v.validate_address("x" * (v.ADDRESS_MAX + 1))
    assert ok is False and reason == "long"


# ----------------------------------------------------------------- comment

def test_comment_empty_is_valid() -> None:
    ok, value = v.validate_comment("")
    assert ok is True and value == ""


def test_comment_too_long() -> None:
    ok, reason = v.validate_comment("x" * (v.COMMENT_MAX + 1))
    assert ok is False and reason == "long"


# ----------------------------------------------------------------- price

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1150000", 1_150_000),
        ("1 150 000", 1_150_000),
        ("1,150,000", 1_150_000),
        ("450000", 450_000),
    ],
)
def test_parse_price_ok(raw: str, expected: int) -> None:
    assert v.parse_price(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "0", "-500", "so'm"])
def test_parse_price_invalid(raw: str) -> None:
    assert v.parse_price(raw) is None


def test_parse_price_rejects_absurd_values() -> None:
    assert v.parse_price(str(v.PRICE_MAX + 1)) is None


# ----------------------------------------------------------------- ints

@pytest.mark.parametrize(("raw", "expected"), [("1", 1), ("42", 42)])
def test_parse_positive_int_ok(raw: str, expected: int) -> None:
    assert v.parse_positive_int(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "", " "])
def test_parse_positive_int_invalid(raw: str) -> None:
    assert v.parse_positive_int(raw) is None
