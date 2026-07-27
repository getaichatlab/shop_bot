"""Language-independent reply-button filter.

`F.text == texts.BTN_CATALOG` breaks the moment a second language exists: the
same button carries a different label per locale. This filter matches the
button by its *key*, in every registered language at once.
"""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from locales import button_variants


class Btn(BaseFilter):
    """Match a reply-keyboard button by locale key, in any language.

    Usage:  @router.message(Btn("BTN_CATALOG"))
    """

    def __init__(self, key: str) -> None:
        self.key = key
        self.variants = button_variants(key)
        if not self.variants:
            raise ValueError(f"Unknown button key: {key}")

    async def __call__(self, message: Message) -> bool:
        return bool(message.text) and message.text in self.variants
