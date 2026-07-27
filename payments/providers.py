"""Payment provider registry.

The bot offers the methods a customer in Uzbekistan or the CIS actually expects
to see. Each provider declares how it collects money, and the handlers read that
declaration instead of branching on names.

Three kinds:

  telegram  Telegram Payments with a provider token (Payme, Click, ЮMoney).
            Needs a merchant account. Without a token the bot shows a realistic
            walkthrough of the flow and says it is a demo.

  manual    Requisites are shown, the customer transfers, then sends a photo of
            the receipt. An admin approves or rejects it. This needs no merchant
            account and works in full today — which is why it is also the
            fallback for every provider whose token is missing.

  stars     Telegram Stars. No merchant account, no token, works everywhere.

  cash      On delivery. The operator collects.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# Regions are only used for grouping in the keyboard, so a Russian customer is
# not made to scroll past Uzbek-only methods to find СБП.
REGION_UZ = "uz"
REGION_CIS = "cis"
REGION_GLOBAL = "global"

KIND_TELEGRAM = "telegram"
KIND_MANUAL = "manual"
KIND_STARS = "stars"
KIND_CASH = "cash"


@dataclass(frozen=True)
class Provider:
    code: str
    kind: str
    region: str
    # Locale keys — the label and the instructions are translated like everything else.
    label_key: str
    # Environment variable holding the Telegram Payments provider token.
    token_env: str = ""
    # Environment variables holding the requisites shown for a manual transfer.
    requisite_envs: tuple[str, ...] = field(default_factory=tuple)
    # Sensible placeholders so a fresh demo still shows a filled-in screen.
    requisite_defaults: tuple[str, ...] = field(default_factory=tuple)

    @property
    def token(self) -> str:
        return os.getenv(self.token_env, "").strip() if self.token_env else ""

    @property
    def is_live(self) -> bool:
        """True when this provider can take real money right now."""
        if self.kind in {KIND_MANUAL, KIND_STARS, KIND_CASH}:
            return True
        return bool(self.token)

    def requisites(self) -> list[str]:
        """Requisite values, falling back to the demo placeholders."""
        out: list[str] = []
        for index, name in enumerate(self.requisite_envs):
            value = os.getenv(name, "").strip()
            if not value and index < len(self.requisite_defaults):
                value = self.requisite_defaults[index]
            out.append(value)
        return out


PROVIDERS: dict[str, Provider] = {
    # ---------------------------------------------------------- Uzbekistan
    "payme": Provider(
        code="payme",
        kind=KIND_TELEGRAM,
        region=REGION_UZ,
        label_key="BTN_PAY_PAYME",
        token_env="PAYME_TOKEN",
    ),
    "click": Provider(
        code="click",
        kind=KIND_TELEGRAM,
        region=REGION_UZ,
        label_key="BTN_PAY_CLICK",
        token_env="CLICK_TOKEN",
    ),
    "card_uz": Provider(
        code="card_uz",
        kind=KIND_MANUAL,
        region=REGION_UZ,
        label_key="BTN_PAY_CARD_UZ",
        requisite_envs=("CARD_UZ_NUMBER", "CARD_UZ_HOLDER", "CARD_UZ_BANK"),
        # Deliberately impossible numbers: a public demo must never look like a
        # card someone could actually send money to.
        requisite_defaults=("0000 0000 0000 0000", "DEMO ACCOUNT", "Humo / Uzcard"),
    ),
    # ---------------------------------------------------------- CIS
    "sbp": Provider(
        code="sbp",
        kind=KIND_MANUAL,
        region=REGION_CIS,
        label_key="BTN_PAY_SBP",
        requisite_envs=("SBP_PHONE", "SBP_HOLDER", "SBP_BANK"),
        requisite_defaults=("+0 000 000-00-00", "DEMO ACCOUNT", "Сбербанк"),
    ),
    "sber": Provider(
        code="sber",
        kind=KIND_MANUAL,
        region=REGION_CIS,
        label_key="BTN_PAY_SBER",
        requisite_envs=("SBER_CARD", "SBER_HOLDER", "SBER_BANK"),
        requisite_defaults=("0000 0000 0000 0000", "DEMO ACCOUNT", "Сбербанк"),
    ),
    "yoomoney": Provider(
        code="yoomoney",
        kind=KIND_TELEGRAM,
        region=REGION_CIS,
        label_key="BTN_PAY_YOOMONEY",
        token_env="YOOMONEY_TOKEN",
    ),
    # ---------------------------------------------------------- global
    "stars": Provider(
        code="stars",
        kind=KIND_STARS,
        region=REGION_GLOBAL,
        label_key="BTN_PAY_STARS",
    ),
    "cash": Provider(
        code="cash",
        kind=KIND_CASH,
        region=REGION_GLOBAL,
        label_key="BTN_PAY_CASH",
    ),
}

# Display order: home market first, then CIS, then the universal fallbacks.
PROVIDER_ORDER: tuple[str, ...] = (
    "payme",
    "click",
    "card_uz",
    "sbp",
    "sber",
    "yoomoney",
    "stars",
    "cash",
)


def get_provider(code: str | None) -> Provider | None:
    return PROVIDERS.get((code or "").lower())


def enabled_codes() -> list[str]:
    """Providers to show, honouring PAYMENT_METHODS in .env when set."""
    raw = os.getenv("PAYMENT_METHODS", "").replace(" ", "")
    if raw:
        chosen = [code for code in raw.split(",") if code in PROVIDERS]
        if chosen:
            return chosen
    return list(PROVIDER_ORDER)


def by_region(codes: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {REGION_UZ: [], REGION_CIS: [], REGION_GLOBAL: []}
    for code in codes:
        provider = PROVIDERS.get(code)
        if provider:
            grouped[provider.region].append(code)
    return grouped
