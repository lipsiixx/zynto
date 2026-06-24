"""Сборка бизнес-роутера (перехват сообщений бизнес-аккаунта)."""
from aiogram import Router

from . import connection, delete_handler, edit_handler, message_handler


def get_business_router() -> Router:
    router = Router(name="business")
    router.include_router(connection.router)
    router.include_router(message_handler.router)
    router.include_router(edit_handler.router)
    router.include_router(delete_handler.router)
    return router
