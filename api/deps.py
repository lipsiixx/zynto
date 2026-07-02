"""FastAPI-зависимости: сессия БД и проверка JWT."""
from __future__ import annotations

import logging
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import verify_token, verify_user_token
from database.engine import SessionLocal
from database.queries import admins as admins_q

logger = logging.getLogger(__name__)

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


# ── WebApp user/admin auth ───────────────────────────────────────────────

async def require_webapp_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    """Проверяет webapp-JWT (пользовательская схема), возвращает telegram_id."""
    tok = creds.credentials if creds else None
    if not tok:
        tok = request.query_params.get("token")
    if not tok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    telegram_id = verify_user_token(tok)
    if telegram_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return telegram_id


async def require_webapp_admin(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Требует, чтобы webapp-пользователь был активным админом.

    Намеренно отдаёт 404 (не 401/403) при ЛЮБОМ отказе — отсутствующий/невалидный/
    просроченный токен и валидный-но-не-админ токен ведут к одному и тому же 404.
    Это не композиция через Depends(require_webapp_user), т.к. та кидает 401 —
    здесь токен разбирается напрямую, чтобы обычный пользователь не мог отличить
    "маршрут существует, но нет прав" от "маршрута не существует".
    """
    tok = creds.credentials if creds else request.query_params.get("token")
    telegram_id = verify_user_token(tok) if tok else None
    if telegram_id is None or not await admins_q.is_admin(db, telegram_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return telegram_id


async def require_webapp_superadmin(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Требует, чтобы webapp-пользователь был активным суперадмином (см. require_webapp_admin)."""
    tok = creds.credentials if creds else request.query_params.get("token")
    telegram_id = verify_user_token(tok) if tok else None
    if telegram_id is None or not await admins_q.is_superadmin(db, telegram_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return telegram_id


async def require_admin_any(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Переходная зависимость для старых monitoring-роутеров.

    Принимает либо старый анонимный admin-panel токен (verify_token — только
    sub=="admin", т.е. логин по паролю), либо новый webapp-токен пользователя,
    являющегося админом (verify_user_token + is_admin). Подключена к роутерам
    users/chats/media/stats/graph/cache (см. Depends(require_admin_any) в них).
    """
    tok = creds.credentials if creds else None
    if not tok:
        tok = request.query_params.get("token")

    if tok and verify_token(tok):
        logger.warning("legacy admin-panel token used on %s", request.url.path)
        return

    telegram_id = verify_user_token(tok) if tok else None
    if telegram_id is not None and await admins_q.is_admin(db, telegram_id):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )
