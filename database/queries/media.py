"""CRUD media_cache."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MediaCache


async def get_by_unique_id(db: AsyncSession, file_unique_id: str) -> MediaCache | None:
    res = await db.execute(select(MediaCache).where(MediaCache.file_unique_id == file_unique_id))
    return res.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    file_unique_id: str,
    file_id: str,
    file_type: str | None,
    file_size: int | None,
    local_path: str | None,
) -> MediaCache:
    cache = await get_by_unique_id(db, file_unique_id)
    now = datetime.now(timezone.utc)
    if cache is None:
        cache = MediaCache(
            file_unique_id=file_unique_id,
            file_id=file_id,
            file_type=file_type,
            file_size=file_size,
            local_path=local_path,
            last_used_at=now,
        )
        db.add(cache)
    else:
        cache.file_id = file_id
        if local_path:
            cache.local_path = local_path
        cache.last_used_at = now
    await db.commit()
    await db.refresh(cache)
    return cache


async def touch(db: AsyncSession, file_unique_id: str) -> None:
    cache = await get_by_unique_id(db, file_unique_id)
    if cache:
        cache.last_used_at = datetime.now(timezone.utc)
        await db.commit()


async def count_all(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(MediaCache.id)))).scalar() or 0)
