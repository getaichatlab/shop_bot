"""Typed settings loaded from .env. No secret is ever hardcoded."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _get_int_list(key: str) -> list[int]:
    raw = os.getenv(key, "").replace(" ", "")
    out: list[int] = []
    for chunk in raw.split(","):
        if chunk:
            try:
                out.append(int(chunk))
            except ValueError:
                continue
    return out


@dataclass(frozen=True)
class BotConfig:
    token: str
    admin_ids: list[int]
    orders_chat_id: int | None


@dataclass(frozen=True)
class WebhookConfig:
    enabled: bool
    base_url: str
    path: str
    secret: str
    host: str
    port: int


@dataclass(frozen=True)
class PaymentConfig:
    provider_token: str
    currency: str
    currency_symbol: str
    # Telegram Stars: no merchant account, no provider token, works worldwide.
    stars_enabled: bool = True
    # "demo" issues a token Stars charge so anyone can walk the whole payment
    # flow; "live" charges the real converted amount.
    mode: str = "demo"
    stars_demo_amount: int = 1
    # Retail price of one Star, in USD. Telegram sells them at roughly $0.02.
    star_price_usd: float = 0.02
    # Telegram expects the amount in the smallest currency unit (tiyin/cent).
    multiplier: int = 100

    @property
    def enabled(self) -> bool:
        """Card payments through an external provider."""
        return bool(self.provider_token)

    @property
    def is_demo(self) -> bool:
        return self.mode != "live"


@dataclass(frozen=True)
class Settings:
    bot: BotConfig
    webhook: WebhookConfig
    payment: PaymentConfig
    db_path: str
    redis_url: str
    fsm_storage: str
    timezone: str
    default_lang: str
    default_currency: str
    throttle_rate: float
    max_open_orders: int
    log_level: str
    log_dir: str
    admin_error_cooldown: int = field(default=60)

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is missing. Copy .env.example to .env and fill it in."
        )

    admin_ids = _get_int_list("ADMIN_IDS")
    if not admin_ids:
        raise RuntimeError(
            "ADMIN_IDS is missing. At least one admin ID is required."
        )

    orders_chat_raw = os.getenv("ORDERS_CHAT_ID", "").strip()
    orders_chat_id: int | None = None
    if orders_chat_raw:
        try:
            orders_chat_id = int(orders_chat_raw)
        except ValueError:
            orders_chat_id = None

    webhook_enabled = _get_bool("USE_WEBHOOK", False)
    webhook_base = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")
    if webhook_enabled and not webhook_base:
        raise RuntimeError("USE_WEBHOOK=true requires WEBHOOK_BASE_URL.")

    webhook_secret = os.getenv("WEBHOOK_SECRET", "").strip()
    if webhook_enabled and not webhook_secret:
        raise RuntimeError(
            "USE_WEBHOOK=true requires WEBHOOK_SECRET "
            "(Telegram secret_token verification)."
        )

    # Non-guessable webhook path: derived from the secret, never the bot token.
    webhook_path = os.getenv("WEBHOOK_PATH", "").strip() or f"/tg/{webhook_secret[:24]}"

    return Settings(
        bot=BotConfig(
            token=token,
            admin_ids=admin_ids,
            orders_chat_id=orders_chat_id,
        ),
        webhook=WebhookConfig(
            enabled=webhook_enabled,
            base_url=webhook_base,
            path=webhook_path,
            secret=webhook_secret,
            host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
            port=_get_int("PORT", 8080),
        ),
        payment=PaymentConfig(
            provider_token=os.getenv("PAYMENT_PROVIDER_TOKEN", "").strip(),
            currency=os.getenv("CURRENCY", "UZS").strip(),
            # Empty by default: the locale decides the symbol per language.
            currency_symbol=os.getenv("CURRENCY_SYMBOL", "").strip(),
            stars_enabled=_get_bool("STARS_ENABLED", True),
            mode=os.getenv("PAYMENT_MODE", "demo").strip().lower(),
            stars_demo_amount=max(1, _get_int("STARS_DEMO_AMOUNT", 1)),
            star_price_usd=float(os.getenv("STAR_PRICE_USD", "0.02") or 0.02),
        ),
        db_path=os.getenv("DB_PATH", "shop.db").strip(),
        redis_url=os.getenv("REDIS_URL", "").strip(),
        fsm_storage=os.getenv("FSM_STORAGE", "sqlite").strip().lower(),
        timezone=os.getenv("TIMEZONE", "Asia/Tashkent").strip(),
        default_lang=os.getenv("DEFAULT_LANG", "ru").strip().lower(),
        default_currency=os.getenv("DEFAULT_CURRENCY", "UZS").strip().upper(),
        throttle_rate=float(os.getenv("THROTTLE_RATE", "0.5")),
        max_open_orders=_get_int("MAX_OPEN_ORDERS", 10),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        log_dir=os.getenv("LOG_DIR", "logs").strip(),
    )


settings = load_settings()
