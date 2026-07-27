"""Payment providers and their capabilities."""
from payments.providers import (
    KIND_CASH,
    KIND_MANUAL,
    KIND_STARS,
    KIND_TELEGRAM,
    PROVIDER_ORDER,
    PROVIDERS,
    Provider,
    by_region,
    enabled_codes,
    get_provider,
)

__all__ = [
    "KIND_CASH",
    "KIND_MANUAL",
    "KIND_STARS",
    "KIND_TELEGRAM",
    "PROVIDERS",
    "PROVIDER_ORDER",
    "Provider",
    "by_region",
    "enabled_codes",
    "get_provider",
]
