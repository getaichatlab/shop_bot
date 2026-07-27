"""Locale registry.

Adding a language:
  1. copy `uz.py`, translate every value, set LANG_CODE / LANG_NAME
  2. import it below and add it to LOCALES

`tests/test_locales.py` fails the build if a locale is missing a key, so a
half-finished translation can never ship.
"""
from __future__ import annotations

from types import ModuleType

from locales import ru, uz

LOCALES: dict[str, ModuleType] = {
    uz.LANG_CODE: uz,
    ru.LANG_CODE: ru,
}

# Order shown in the language picker.
LANGUAGE_ORDER: tuple[str, ...] = ("ru", "uz")

FALLBACK_LANG = "ru"


def get_texts(lang: str | None) -> ModuleType:
    """Return the locale module, falling back when the code is unknown."""
    return LOCALES.get(lang or "", LOCALES[FALLBACK_LANG])


def is_supported(lang: str | None) -> bool:
    return lang in LOCALES


def language_name(lang: str) -> str:
    return get_texts(lang).LANG_NAME


def button_variants(key: str) -> set[str]:
    """Every translation of one button label.

    Reply-keyboard handlers match on button text, so a handler must accept the
    label in whichever language the user currently has selected — and also in
    the language they had a moment before switching.
    """
    values: set[str] = set()
    for module in LOCALES.values():
        value = getattr(module, key, None)
        if isinstance(value, str):
            values.add(value)
    return values


__all__ = [
    "FALLBACK_LANG",
    "LANGUAGE_ORDER",
    "LOCALES",
    "button_variants",
    "get_texts",
    "is_supported",
    "language_name",
]
