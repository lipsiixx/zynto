"""FastAPI-зависимости: сессия БД и проверка JWT."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import verify_token
from database.engine import SessionLocal

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def require_auth(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    # Токен из заголовка Authorization: Bearer <tok>
    tok = creds.credentials if creds else None
    # Запасной вариант: ?token=<tok> в строке запроса (нужен для <img src> и <audio src>)
    if not tok:
        tok = request.query_params.get("token")
    if not tok or not verify_token(tok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
