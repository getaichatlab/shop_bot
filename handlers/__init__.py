"""Handler routers, in registration order.

`common` first (start/cancel must always win), `admin` last because its
router-level filter would otherwise shadow shared buttons.
"""
from aiogram import Router

from handlers import admin, cart, catalog, common, errors, order, payment


def build_router() -> Router:
    root = Router(name="root")
    root.include_router(common.router)
    root.include_router(catalog.router)
    root.include_router(cart.router)
    root.include_router(order.router)
    root.include_router(payment.router)
    root.include_router(admin.router)
    root.include_router(errors.router)
    return root


__all__ = ["build_router"]
