"""CRUD админов."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin


async def get_admin(db: AsyncSession, telegram_id: int) -> Admin | None:
    res = await db.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    return res.scalar_one_or_none()


async def is_admin(db: AsyncSession, telegram_id: int) -> bool:
    admin = await get_admin(db, telegram_id)
    return admin is not None and admin.is_active


async def is_superadmin(db: AsyncSession, telegram_id: int) -> bool:
    admin = await get_admin(db, telegram_id)
    return admin is not None and admin.is_active and admin.is_superadmin


async def list_admins(db: AsyncSession, include_superadmin: bool = True) -> list[Admin]:
    stmt = select(Admin).where(Admin.is_active == True)  # noqa: E712
    if not include_superadmin:
        stmt = stmt.where(Admin.is_superadmin == False)  # noqa: E712
    stmt = stmt.order_by(Admin.created_at)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def ensure_superadmin(db: AsyncSession, telegram_id: int) -> None:
    """Создаёт/активирует суперадмина из .env при старте."""
    if telegram_id <= 0:
        return
    admin = await get_admin(db, telegram_id)
    if admin is None:
        db.add(Admin(telegram_id=telegram_id, is_superadmin=True, is_active=True))
    else:
        admin.is_superadmin = True
        admin.is_active = True
    await db.commit()


async def add_admin(
    db: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    added_by: int,
) -> Admin:
    admin = await get_admin(db, telegram_id)
    if admin is None:
        admin = Admin(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            added_by=added_by,
            is_active=True,
        )
        db.add(admin)
    else:
        admin.is_active = True
        admin.username = username
        admin.full_name = full_name
    await db.commit()
    await db.refresh(admin)
    return admin


async def remove_admin(db: AsyncSession, telegram_id: int) -> None:
    await db.execute(
        update(Admin)
        .where(Admin.telegram_id == telegram_id, Admin.is_superadmin == False)  # noqa: E712
        .values(is_active=False)
    )
    await db.commit()
