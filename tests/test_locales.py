"""Locale integrity: a half-finished translation must fail the build."""
from __future__ import annotations

import string

import pytest

from locales import (
    FALLBACK_LANG,
    LANGUAGE_ORDER,
    LOCALES,
    button_variants,
    get_texts,
    is_supported,
)

REFERENCE = "uz"


def _public_keys(module) -> set[str]:
    return {
        name
        for name in dir(module)
        if name.isupper() and not name.startswith("_")
    }


def _placeholders(template: str) -> set[str]:
    return {
        field
        for _, field, _, _ in string.Formatter().parse(template)
        if field
    }


def test_at_least_two_languages() -> None:
    assert len(LOCALES) >= 2


def test_every_locale_has_the_same_keys() -> None:
    reference_keys = _public_keys(LOCALES[REFERENCE])
    for code, module in LOCALES.items():
        missing = reference_keys - _public_keys(module)
        assert not missing, f"locale '{code}' is missing: {sorted(missing)}"


def test_no_locale_has_extra_keys() -> None:
    reference_keys = _public_keys(LOCALES[REFERENCE])
    for code, module in LOCALES.items():
        extra = _public_keys(module) - reference_keys
        assert not extra, f"locale '{code}' has undeclared keys: {sorted(extra)}"


def test_placeholders_match_across_locales() -> None:
    """`{order_id}` in one language must exist in every other language."""
    reference = LOCALES[REFERENCE]
    for key in _public_keys(reference):
        ref_value = getattr(reference, key)
        if not isinstance(ref_value, str):
            continue
        expected = _placeholders(ref_value)
        for code, module in LOCALES.items():
            value = getattr(module, key)
            assert isinstance(value, str), f"{code}.{key} should be a string"
            assert _placeholders(value) == expected, (
                f"{code}.{key} placeholders {_placeholders(value)} "
                f"!= {REFERENCE}.{key} {expected}"
            )


def test_no_empty_strings() -> None:
    for code, module in LOCALES.items():
        for key in _public_keys(module):
            value = getattr(module, key)
            if isinstance(value, str):
                assert value.strip(), f"{code}.{key} is empty"


def test_status_labels_cover_every_status() -> None:
    statuses = {"new", "accepted", "paid", "shipping", "done", "canceled"}
    for code, module in LOCALES.items():
        assert statuses <= set(module.STATUS_LABELS), f"locale '{code}' misses a status"


def test_button_labels_are_unique_within_a_locale() -> None:
    """Two buttons sharing a label would make the Btn filter ambiguous."""
    for code, module in LOCALES.items():
        labels = [
            getattr(module, key)
            for key in _public_keys(module)
            if key.startswith("BTN_")
        ]
        assert len(labels) == len(set(labels)), f"duplicate button label in '{code}'"


def test_button_variants_collects_every_language() -> None:
    variants = button_variants("BTN_CATALOG")
    assert len(variants) == len(LOCALES)
    assert LOCALES["uz"].BTN_CATALOG in variants
    assert LOCALES["ru"].BTN_CATALOG in variants


def test_button_variants_of_unknown_key_is_empty() -> None:
    assert button_variants("BTN_DOES_NOT_EXIST") == set()


@pytest.mark.parametrize("code", ["uz", "ru"])
def test_supported_codes(code: str) -> None:
    assert is_supported(code)
    assert get_texts(code).LANG_CODE == code


@pytest.mark.parametrize("code", [None, "", "de", "xx", "UZ"])
def test_unknown_code_falls_back(code) -> None:
    assert not is_supported(code)
    assert get_texts(code).LANG_CODE == FALLBACK_LANG


def test_language_order_is_valid() -> None:
    assert set(LANGUAGE_ORDER) == set(LOCALES)


def test_locales_are_actually_different() -> None:
    assert LOCALES["uz"].BTN_CATALOG != LOCALES["ru"].BTN_CATALOG
    assert LOCALES["uz"].WELCOME != LOCALES["ru"].WELCOME
