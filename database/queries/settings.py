"""Работа с таблицей bot_settings."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as cfg
from database.models import BotSetting

logger = logging.getLogger(__name__)


async def get_setting(db: AsyncSession, key: str, default: str | None = None) -> str | None:
    res = await db.execute(select(BotSetting).where(BotSetting.key == key))
    row = res.scalar_one_or_none()
    return row.value if row else default


async def get_int_setting(db: AsyncSession, key: str, default: int) -> int:
    raw = await get_setting(db, key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


async def get_json_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    """Читает bot_settings[key], парсит JSON, при ошибке возвращает default."""
    raw = await get_setting(db, key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Не удалось распарсить JSON-настройку %s", key)
        return default


async def set_json_setting(db: AsyncSession, key: str, value: Any, updated_by: int | None = None) -> None:
    """Сериализует value в JSON и сохраняет в bot_settings[key]."""
    await set_setting(db, key, json.dumps(value, ensure_ascii=False), updated_by=updated_by)


async def set_setting(db: AsyncSession, key: str, value: str, updated_by: int | None = None) -> None:
    res = await db.execute(select(BotSetting).where(BotSetting.key == key))
    row = res.scalar_one_or_none()
    if row is None:
        db.add(BotSetting(key=key, value=value, updated_by=updated_by))
    else:
        row.value = value
        row.updated_by = updated_by
    await db.commit()


async def ensure_defaults(db: AsyncSession) -> None:
    """Создаёт настройки очистки по умолчанию из .env, если их ещё нет."""
    if await get_setting(db, "text_retention_days") is None:
        await set_setting(db, "text_retention_days", str(cfg.text_retention_days))
    if await get_setting(db, "media_retention_days") is None:
        await set_setting(db, "media_retention_days", str(cfg.media_retention_days))
    if await get_setting(db, "log_retention_days") is None:
        await set_setting(db, "log_retention_days", str(cfg.log_retention_days))
    if await get_setting(db, "referral_bonus_days") is None:
        await set_setting(db, "referral_bonus_days", "1")
    if await get_setting(db, "referral_reward_days") is None:
        await set_setting(db, "referral_reward_days", "3")
    if await get_setting(db, "referral_enabled") is None:
        await set_setting(db, "referral_enabled", "1")
    if await get_setting(db, "course_enabled") is None:
        await set_setting(db, "course_enabled", "0")
    if await get_setting(db, "course_caption") is None:
        await set_setting(db, "course_caption", "📚 Курс по использованию бота")
    if await get_setting(db, "nudge_enabled") is None:
        await set_setting(db, "nudge_enabled", "0")
    if await get_setting(db, "nudge_interval_days") is None:
        await set_setting(db, "nudge_interval_days", "1")
    if await get_setting(db, "nudge_grace_days") is None:
        await set_setting(db, "nudge_grace_days", "3")
    if await get_setting(db, "about_privacy_enabled") is None:
        await set_setting(db, "about_privacy_enabled", "1")
    if await get_setting(db, "about_privacy_type") is None:
        await set_setting(db, "about_privacy_type", "text")
    if await get_setting(db, "about_privacy_content") is None:
        await set_setting(db, "about_privacy_content", "")
    if await get_setting(db, "about_terms_enabled") is None:
        await set_setting(db, "about_terms_enabled", "1")
    if await get_setting(db, "about_terms_type") is None:
        await set_setting(db, "about_terms_type", "text")
    if await get_setting(db, "about_terms_content") is None:
        await set_setting(db, "about_terms_content", "")
    if await get_setting(db, "about_support_enabled") is None:
        await set_setting(db, "about_support_enabled", "1")
    if await get_setting(db, "about_support_url") is None:
        await set_setting(db, "about_support_url", "")
