"""FastAPI-зависимости: сессия БД и проверка JWT."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import verify_token
from database.engine import SessionLocal

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if creds is None or not verify_token(creds.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
