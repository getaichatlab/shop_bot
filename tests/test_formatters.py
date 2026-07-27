"""Unit tests for formatting helpers. Run: pytest -q"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# config.py validates the environment on import — provide safe test values.
os.environ.setdefault("BOT_TOKEN", "111:TEST")
os.environ.setdefault("ADMIN_IDS", "1")

from utils.formatters import esc, fmt_dt, fmt_price, split_message, to_local  # noqa: E402
from utils.validators import MAX_MESSAGE_LEN  # noqa: E402


# ----------------------------------------------------------------- money

def test_fmt_price_groups_thousands() -> None:
    assert fmt_price(1_150_000).startswith("1 150 000")


def test_fmt_price_small_value() -> None:
    assert fmt_price(500).startswith("500")


def test_fmt_price_zero() -> None:
    assert fmt_price(0).startswith("0")


# ----------------------------------------------------------------- escaping

def test_esc_neutralizes_html() -> None:
    assert esc("<b>hack</b>") == "&lt;b&gt;hack&lt;/b&gt;"


def test_esc_handles_ampersand() -> None:
    assert esc("Tom & Jerry") == "Tom &amp; Jerry"


def test_esc_accepts_non_strings() -> None:
    assert esc(42) == "42"


# ----------------------------------------------------------------- time

def test_to_local_converts_utc_string() -> None:
    local = to_local("2026-07-26T10:00:00Z")
    assert local is not None
    # Asia/Tashkent is UTC+5 year-round.
    assert local.hour == 15


def test_to_local_handles_bad_input() -> None:
    assert to_local("not-a-date") is None
    assert to_local(None) is None


def test_fmt_dt_fallback() -> None:
    assert fmt_dt(None) == "—"


# ----------------------------------------------------------------- splitting

def test_split_short_message_is_untouched() -> None:
    assert split_message("hello") == ["hello"]


def test_split_respects_limit() -> None:
    text = "\n".join("line" * 50 for _ in range(200))
    chunks = split_message(text)
    assert len(chunks) > 1
    assert all(len(c) <= MAX_MESSAGE_LEN for c in chunks)


def test_split_hard_splits_a_single_huge_line() -> None:
    text = "x" * (MAX_MESSAGE_LEN * 2 + 10)
    chunks = split_message(text)
    assert all(len(c) <= MAX_MESSAGE_LEN for c in chunks)
    assert "".join(chunks) == text


def test_split_preserves_content() -> None:
    lines = [f"line-{i}" for i in range(2000)]
    text = "\n".join(lines)
    chunks = split_message(text)
    rejoined = "\n".join(chunks)
    for line in (lines[0], lines[-1], lines[1000]):
        assert line in rejoined


@pytest.mark.parametrize("size", [1, 100, MAX_MESSAGE_LEN, MAX_MESSAGE_LEN + 1])
def test_split_never_exceeds_limit(size: int) -> None:
    chunks = split_message("a" * size)
    assert all(len(c) <= MAX_MESSAGE_LEN for c in chunks)
