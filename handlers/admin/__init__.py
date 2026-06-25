"""Сборка админского роутера."""
from aiogram import Router

from . import (
    admins_mgmt,
    cleanup,
    panel,
    promo,
    proxy,
    server,
    stats,
    tariffs,
    users_mgmt,
)


def get_admin_router() -> Router:
    router = Router(name="admin")
    router.include_router(panel.router)
    router.include_router(tariffs.router)
    router.include_router(promo.router)
    router.include_router(stats.router)
    router.include_router(server.router)
    router.include_router(proxy.router)
    router.include_router(users_mgmt.router)
    router.include_router(admins_mgmt.router)
    router.include_router(cleanup.router)
    return router
