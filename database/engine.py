"""Async engine, sessionmaker и инициализация БД."""
from __future__ import annotations

import logging

import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings
from database.models import Base

logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


def _parse_db_name(url: str) -> tuple[str, str]:
    """Возвращает (url_к_серверу_postgres, имя_базы) из SQLAlchemy URL."""
    # postgresql+asyncpg://user:pass@host:port/dbname
    raw = url.split("://", 1)[1]
    creds_host, dbname = raw.rsplit("/", 1)
    return creds_host, dbname


async def ensure_database_exists() -> None:
    """Создаёт базу данных, если её ещё нет (подключаясь к служебной базе postgres)."""
    creds_host, dbname = _parse_db_name(settings.database_url)
    dsn = f"postgresql://{creds_host}/postgres"
    try:
        conn = await asyncpg.connect(dsn=dsn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось подключиться к служебной базе postgres: %s", exc)
        return
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{dbname}"')
            logger.info("База данных %s создана", dbname)
    finally:
        await conn.close()


async def _alembic_managed(conn) -> bool:
    """True, если в БД есть таблица alembic_version (схемой управляет Alembic)."""
    from sqlalchemy import inspect

    def _check(sync_conn) -> bool:
        return inspect(sync_conn).has_table("alembic_version")

    return await conn.run_sync(_check)


async def init_db() -> None:
    """Готовит схему БД.

    Если БД под управлением Alembic (есть alembic_version) — ничего не создаём,
    источник истины это миграции (`alembic upgrade head`). Иначе создаём схему
    из моделей через create_all — режим zero-config для быстрого старта.
    """
    await ensure_database_exists()
    async with engine.begin() as conn:
        if await _alembic_managed(conn):
            logger.info("Схема под управлением Alembic — пропускаю create_all")
            return
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Схема БД готова (create_all)")


async def dispose_db() -> None:
    await engine.dispose()
