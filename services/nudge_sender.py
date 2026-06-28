"""Отправка подначивающих сообщений пользователям с истёкшей подпиской."""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from database.engine import SessionLocal
from database.queries import nudge as nudge_q
from database.queries import settings as settings_q
from keyboards.user_kb import nudge_kb

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))
WINDOW_START = 10  # 10:00 МСК
WINDOW_END = 21    # до 21:00 МСК


def _rand_time_on_date(date) -> datetime:
    """Случайный datetime в окне [10:00, 21:00) на указанную дату (MSK)."""
    h = random.randint(WINDOW_START, WINDOW_END - 1)
    m = random.randint(0, 59)
    return datetime(date.year, date.month, date.day, h, m, tzinfo=MSK)


def _first_send_time() -> datetime:
    """Для нового кандидата: сегодня если осталось ≥60 мин в окне, иначе — завтра."""
    now_msk = datetime.now(MSK)
    window_close = now_msk.replace(hour=WINDOW_END, minute=0, second=0, microsecond=0)
    remaining_min = (window_close - now_msk).total_seconds() / 60
    if remaining_min >= 60:
        earliest = now_msk + timedelta(minutes=10)
        latest = window_close - timedelta(minutes=10)
        if earliest < latest:
            offset = random.randint(0, int((latest - earliest).total_seconds() // 60))
            return earliest + timedelta(minutes=offset)
    tomorrow = (now_msk + timedelta(days=1)).date()
    return _rand_time_on_date(tomorrow)


def _next_send_time(interval_days: int) -> datetime:
    """Случайное время через interval_days дней в окне [10:00, 21:00) МСК."""
    now_msk = datetime.now(MSK)
    target_date = (now_msk + timedelta(days=interval_days)).date()
    return _rand_time_on_date(target_date)


async def run_nudge_job(bot: Bot) -> None:
    async with SessionLocal() as db:
        enabled = await settings_q.get_setting(db, "nudge_enabled", "0")
        if enabled != "1":
            return

        interval_days = await settings_q.get_int_setting(db, "nudge_interval_days", 1)
        grace_days = await settings_q.get_int_setting(db, "nudge_grace_days", 3)

        # Назначаем время первой отправки новым кандидатам
        new_candidates = await nudge_q.get_users_to_schedule(db, grace_days)
        for user in new_candidates:
            user.nudge_next_at = _first_send_time()
        if new_candidates:
            await db.commit()
            logger.info("Nudge: назначено %d новых кандидатов", len(new_candidates))

        # Отправляем тем, у кого nudge_next_at уже наступил
        due_users = await nudge_q.get_users_due_for_nudge(db)
        if not due_users:
            return

        nudge_msg = await nudge_q.get_random_active_nudge(db)
        now_utc = datetime.now(timezone.utc)

        for user in due_users:
            if nudge_msg is not None:
                try:
                    await bot.send_message(
                        user.telegram_id, nudge_msg.text,
                        parse_mode="HTML", reply_markup=nudge_kb(),
                    )
                    user.nudge_sent_at = now_utc
                    logger.info("Nudge отправлен: user=%s", user.telegram_id)
                except TelegramForbiddenError:
                    user.is_blocked = True
                    logger.info("Nudge: user=%s заблокировал бота", user.telegram_id)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Nudge: ошибка отправки user=%s: %s", user.telegram_id, exc)
            # Перепланируем вне зависимости от результата
            user.nudge_next_at = _next_send_time(interval_days)

        await db.commit()
        logger.info("Nudge: обработано %d пользователей", len(due_users))
