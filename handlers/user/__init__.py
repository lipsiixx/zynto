"""Сборка пользовательского роутера."""
from aiogram import Router

from . import activate_code, course, gift, history, media_gallery, referral, start, subscription


def get_user_router() -> Router:
    router = Router(name="user")
    router.include_router(start.router)
    router.include_router(subscription.router)
    router.include_router(activate_code.router)
    router.include_router(course.router)
    router.include_router(history.router)
    router.include_router(media_gallery.router)
    router.include_router(gift.router)
    router.include_router(referral.router)
    return router
