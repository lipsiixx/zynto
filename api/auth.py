"""JWT-аутентификация REST API (admin + webapp user)."""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings

_ALG = "HS256"
_TTL_DAYS = 7
_USER_TTL_HOURS = 24

router = APIRouter(tags=["auth"])


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
    try:
        jwt.decode(token, settings.api_secret, algorithms=[_ALG])
        return True
    except jwt.PyJWTError:
        return False


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    if not settings.api_password or body.password != settings.api_password:
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
