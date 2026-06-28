"""CRUD media_cache."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
    content_hash: str | None = None,
) -> MediaCache | None:
    """Атомарный upsert (INSERT ... ON CONFLICT) — без гонки при параллельном кешировании.

    Прежняя «проверить-потом-вставить» падала UniqueViolation, когда одно и то же
    медиа кешировалось двумя апдейтами одновременно. ON CONFLICT снимает гонку на
    уровне БД. local_path и content_hash обновляем только если переданы непустыми."""
    now = datetime.now(timezone.utc)
    set_ = {"file_id": file_id, "last_used_at": now}
    if local_path:
        set_["local_path"] = local_path
    if content_hash:
        set_["content_hash"] = content_hash
    stmt = (
        pg_insert(MediaCache)
        .values(
            file_unique_id=file_unique_id,
            file_id=file_id,
            file_type=file_type,
            file_size=file_size,
            local_path=local_path,
            content_hash=content_hash,
            last_used_at=now,
        )
        .on_conflict_do_update(index_elements=["file_unique_id"], set_=set_)
    )
    await db.execute(stmt)
    await db.commit()
    return await get_by_unique_id(db, file_unique_id)


async def touch(db: AsyncSession, file_unique_id: str) -> None:
    cache = await get_by_unique_id(db, file_unique_id)
    if cache:
        cache.last_used_at = datetime.now(timezone.utc)
        await db.commit()


async def count_all(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(MediaCache.id)))).scalar() or 0)
