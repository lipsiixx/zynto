"""JWT-аутентификация REST API (admin + webapp user)."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import settings

_ALG = "HS256"
_TTL_DAYS = 7
_USER_TTL_HOURS = 24

router = APIRouter(tags=["auth"])

# /auth/login — единственный вход в легаси admin-панель по паролю (без привязки
# к Telegram-аккаунту), значит без защиты от подбора это просто угадывание
# API_PASSWORD. Простой in-memory rate-limit по IP — процесс один (uvicorn без
# нескольких воркеров), так что общий словарь в памяти достаточен.
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 300
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _login_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    attempts = _login_attempts[ip]
    attempts[:] = [t for t in attempts if now - t < _LOGIN_WINDOW_SECONDS]
    return len(attempts) >= _LOGIN_MAX_ATTEMPTS


def _register_failed_login(ip: str) -> None:
    _login_attempts[ip].append(time.monotonic())


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    token: str
    expiresAt: datetime


def create_token() -> tuple[str, datetime]:
    exp = datetime.now(timezone.utc) + timedelta(days=_TTL_DAYS)
    token = jwt.encode({"sub": "admin", "exp": exp}, settings.api_secret, algorithm=_ALG)
    return token, exp


def verify_token(token: str) -> bool:
    """True только для легаси admin-токена (логин по паролю, sub == "admin").

    Проверять именно sub, а не только подпись: пользовательские webapp-токены
    (`create_user_token`, sub == "user:<id>") подписаны тем же секретом и иначе
    прошли бы эту проверку, открыв любому залогиненному пользователю мини-аппа
    доступ к require_auth/require_admin_any-роутерам (/v1/users, /v1/chats, …).
    """
    try:
        payload = jwt.decode(token, settings.api_secret, algorithms=[_ALG])
    except jwt.PyJWTError:
        return False
    return payload.get("sub") == "admin"


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    if _login_rate_limited(ip):
        raise HTTPException(status_code=429, detail="too_many_attempts")
    if not settings.api_password or body.password != settings.api_password:
        _register_failed_login(ip)
        raise HTTPException(status_code=401, detail="invalid_password")
    token, exp = create_token()
    return TokenResponse(token=token, expiresAt=exp)


# ── WebApp user tokens ─────────────────────────────────────────────────────

def create_user_token(telegram_id: int) -> tuple[str, datetime]:
    exp = datetime.now(timezone.utc) + timedelta(hours=_USER_TTL_HOURS)
    token = jwt.encode(
        {"sub": f"user:{telegram_id}", "exp": exp},
        settings.api_secret,
        algorithm=_ALG,
    )
    return token, exp


def verify_user_token(token: str) -> int | None:
    """Returns telegram_id if valid webapp user token, else None."""
    try:
        payload = jwt.decode(token, settings.api_secret, algorithms=[_ALG])
        sub = payload.get("sub", "")
        if sub.startswith("user:"):
            return int(sub[5:])
        return None
    except (jwt.PyJWTError, ValueError):
        return None


def verify_webapp_init_data(init_data: str) -> dict | None:
    """Validate Telegram WebApp initData HMAC. Returns parsed user dict or None."""
    if not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:  # noqa: BLE001
        return None

    received_hash = parsed.pop("hash", "")
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode(), hashlib.sha256
    ).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    try:
        return json.loads(parsed.get("user", "{}"))
    except json.JSONDecodeError:
        return None
