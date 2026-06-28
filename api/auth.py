"""JWT-аутентификация REST API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings

_ALG = "HS256"
_TTL_DAYS = 7

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
