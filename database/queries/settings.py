"""Работа с таблицей bot_settings."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as cfg
from database.models import BotSetting


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
