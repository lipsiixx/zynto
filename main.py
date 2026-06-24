"""Точка входа: инициализация и запуск Telegram-бота мониторинга."""
from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, ErrorEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis.asyncio import Redis

from config import settings
from database.engine import SessionLocal, dispose_db, init_db
from database.queries import admins as admins_q
from database.queries import settings as settings_q
from database.queries import tariffs as tariffs_q
from handlers.admin import get_admin_router
from handlers.business import get_business_router
from handlers.user import get_user_router
from middlewares.admin_check import AdminCheckMiddleware
from middlewares.auth import AuthMiddleware
from middlewares.database import DatabaseMiddleware
from middlewares.throttle import ThrottleMiddleware
from services import cleaner, media
from services import notifier as notifier_module
from services.notifier import Notifier
from services.subscription import check_expired_subscriptions

logger = logging.getLogger(__name__)

ALLOWED_UPDATES = [
    "message",
    "edited_message",
    "callback_query",
    "business_connection",
    "business_message",
    "edited_business_message",
    "deleted_business_messages",
    "pre_checkout_query",
]

DEFAULT_TARIFFS = [
    # (name, description, duration_days, price_stars, sort_order)
    ("1 месяц", "Доступ к мониторингу на 30 дней", 30, 99, 1),
    ("3 месяца", "Доступ к мониторингу на 90 дней", 90, 249, 2),
    ("Навсегда", "Пожизненный доступ", None, 799, 3),
]


def setup_logging() -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)

    file_handler = RotatingFileHandler(
        settings.logs_dir / "bot.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    logging.basicConfig(level=level, handlers=[stream, file_handler])
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def seed_data() -> None:
    """Суперадмин, настройки очистки и стартовые тарифы."""
    async with SessionLocal() as db:
        await admins_q.ensure_superadmin(db, settings.superadmin_id)
        await settings_q.ensure_defaults(db)
        existing = await tariffs_q.list_tariffs(db, only_active=False)
        if not existing:
            for name, desc, days, price, order in DEFAULT_TARIFFS:
                await tariffs_q.create_tariff(
                    db, name=name, description=desc, duration_days=days,
                    price_stars=price, sort_order=order, created_by=settings.superadmin_id,
                )
            logger.info("Созданы стартовые тарифы")


def setup_middlewares(dp: Dispatcher, user_router, admin_router, redis: Redis | None) -> None:
    # database — внешний middleware для всех апдейтов
    dp.update.outer_middleware(DatabaseMiddleware())

    # auth + throttle — только для пользовательских апдейтов
    user_router.message.middleware(AuthMiddleware())
    user_router.callback_query.middleware(AuthMiddleware())
    user_router.message.middleware(ThrottleMiddleware(redis))
    user_router.callback_query.middleware(ThrottleMiddleware(redis))

    # admin_check — только для админских апдейтов
    admin_router.message.middleware(AdminCheckMiddleware())
    admin_router.callback_query.middleware(AdminCheckMiddleware())


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(cleaner.run_cleanup, "interval", hours=24, id="cleanup")
    scheduler.add_job(check_expired_subscriptions, "interval", minutes=60, id="check_expired")
    return scheduler


def register_error_handler(dp: Dispatcher, bot: Bot) -> None:
    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        logger.exception("Необработанная ошибка: %s", event.exception)
        if settings.superadmin_id:
            try:
                await bot.send_message(
                    settings.superadmin_id,
                    f"⚠️ Ошибка в боте:\n<code>{type(event.exception).__name__}: {event.exception}</code>",
                )
            except Exception:  # noqa: BLE001
                pass
        return True


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск / главное меню"),
        BotCommand(command="activate", description="Активировать промокод"),
        BotCommand(command="myid", description="Узнать свой Telegram ID"),
        BotCommand(command="admin", description="Админ-панель"),
    ])


async def main() -> None:
    setup_logging()
    settings.validate()
    logger.info("Запуск бота…")

    await init_db()
    await seed_data()
    media.ensure_media_dirs()

    # Redis (для FSM и throttle); если недоступен — продолжаем без него.
    # protocol=2 для совместимости со старыми серверами (Redis < 6, без RESP3/HELLO).
    redis: Redis | None = None
    storage = MemoryStorage()
    try:
        redis = Redis.from_url(settings.redis_url, protocol=2, decode_responses=True)
        await redis.ping()
        storage = RedisStorage(redis=Redis.from_url(settings.redis_url, protocol=2))
        logger.info("Redis подключён: %s", settings.redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis недоступен (%s). FSM в памяти, throttle отключён.", exc)
        redis = None

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    # Notifier (очередь уведомлений)
    notifier_module.notifier = Notifier(bot)
    notifier_module.notifier.start()

    user_router = get_user_router()
    admin_router = get_admin_router()
    business_router = get_business_router()

    setup_middlewares(dp, user_router, admin_router, redis)

    # порядок: бизнес → админ → пользователь
    dp.include_router(business_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)

    register_error_handler(dp, bot)

    scheduler = setup_scheduler()
    scheduler.start()

    await set_commands(bot)

    try:
        me = await bot.get_me()
        logger.info("Бот @%s запущен", me.username)
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
    finally:
        scheduler.shutdown(wait=False)
        await notifier_module.notifier.stop()
        if redis is not None:
            await redis.aclose()
        await bot.session.close()
        await dispose_db()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
