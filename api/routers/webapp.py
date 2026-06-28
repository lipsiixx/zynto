"""WebApp API — пользовательский мини-апп."""
from __future__ import annotations

import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import create_user_token, verify_user_token, verify_webapp_init_data
from api.deps import get_db
from config import BASE_DIR
from database.models import MediaCache, MessageLog, User
from database.queries import promo_codes as promo_q
from database.queries import settings as settings_q
from database.queries import tariffs as tariffs_q
from database.queries import users as users_q
from database.queries import webapp as webapp_q
from services import subscription as sub_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webapp", tags=["webapp"])
_bearer = HTTPBearer(auto_error=False)


# ── Auth helper ───────────────────────────────────────────────────────────

async def _require_webapp_auth(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    tok = creds.credentials if creds else None
    if not tok:
        tok = request.query_params.get("token")
    if not tok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    telegram_id = verify_user_token(tok)
    if telegram_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return telegram_id


def _get_bot(request: Request) -> Bot | None:
    return getattr(request.app.state, "bot", None)


# ── Schemas ───────────────────────────────────────────────────────────────

class WebAppAuthRequest(BaseModel):
    initData: str


class WebAppAuthResponse(BaseModel):
    token: str
    expiresAt: datetime
    user: dict


class TrustSetRequest(BaseModel):
    score: Optional[int] = None  # None = reset to auto


class ActivateRequest(BaseModel):
    code: str


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/auth", response_model=WebAppAuthResponse)
async def webapp_auth(
    body: WebAppAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> WebAppAuthResponse:
    """Верифицирует Telegram initData и возвращает JWT."""
    user_data = verify_webapp_init_data(body.initData)
    if user_data is None:
        # For local development, allow test mode without real initData
        # In production this is always verified
        from config import settings
        if not settings.test_mode:
            raise HTTPException(status_code=401, detail="invalid_init_data")
        # Test mode: try to parse as JSON directly
        try:
            import json
            user_data = json.loads(body.initData)
        except Exception:
            raise HTTPException(status_code=401, detail="invalid_init_data")

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="no_user_id")

    user = await users_q.get_user(db, telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    token, exp = create_user_token(telegram_id)
    return WebAppAuthResponse(token=token, expiresAt=exp, user=user_data)


@router.get("/me")
async def webapp_me(
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.get_user(db, telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    has_sub = sub_service.has_active_subscription(user)
    summary = await webapp_q.get_user_summary(db, telegram_id)

    from database.queries import business as biz_q
    conn = await biz_q.get_active_for_user(db, telegram_id)

    expires_at = None
    if user.subscription_expires_at:
        expires_at = user.subscription_expires_at.isoformat()

    return {
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "username": user.username,
        "avatar_file_id": user.avatar_file_id,
        "subscription": {
            "status": user.subscription_status,
            "has_active": has_sub,
            "expires_at": expires_at,
        },
        "monitoring_active": conn is not None,
        "summary": summary,
    }


@router.get("/contacts")
async def webapp_contacts(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    contacts, total = await webapp_q.get_user_contacts(db, telegram_id, q=q, page=page, limit=limit)
    for c in contacts:
        if c.get("last_message_at"):
            c["last_message_at"] = c["last_message_at"].isoformat()
    return {
        "data": contacts,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/contacts/{chat_id}/events")
async def webapp_contact_events(
    chat_id: int,
    flt: str = Query("all", description="all|deleted|edited|media"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    events, total = await webapp_q.get_contact_events(db, telegram_id, chat_id, flt=flt, page=page, limit=limit)

    def _fmt(e) -> dict:
        return {
            "id": e.id,
            "message_id": e.message_id,
            "is_outgoing": e.is_outgoing,
            "is_deleted": e.is_deleted,
            "is_edited": e.is_edited,
            "message_type": e.message_type,
            "text_content": e.text_content,
            "original_text": e.original_text,
            "file_id": e.file_id,
            "file_unique_id": e.file_unique_id,
            "mime_type": e.mime_type,
            "duration_seconds": e.duration_seconds,
            "width": e.width,
            "height": e.height,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "deleted_at": e.deleted_at.isoformat() if e.deleted_at else None,
            "edited_at": e.edited_at.isoformat() if e.edited_at else None,
        }

    return {"data": [_fmt(e) for e in events], "total": total, "page": page}


@router.get("/contacts/{chat_id}/stats")
async def webapp_contact_stats(
    chat_id: int,
    days: int = Query(30, ge=7, le=90),
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await webapp_q.get_contact_stats(db, telegram_id, chat_id, days=days)
    return {"data": data, "days": days}


@router.put("/trust/{chat_id}")
async def webapp_set_trust(
    chat_id: int,
    body: TrustSetRequest,
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.score is None:
        await webapp_q.clear_trust_score(db, telegram_id, chat_id)
        return {"chat_id": chat_id, "manual_score": None}
    if not 0 <= body.score <= 100:
        raise HTTPException(status_code=422, detail="score_out_of_range")
    await webapp_q.set_trust_score(db, telegram_id, chat_id, body.score)
    return {"chat_id": chat_id, "manual_score": body.score}


@router.get("/tariffs")
async def webapp_tariffs(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(_require_webapp_auth),
) -> dict:
    tariffs = await tariffs_q.list_tariffs(db, only_active=True)
    return {
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "duration_days": t.duration_days,
                "price_stars": t.price_stars,
            }
            for t in tariffs
        ]
    }


@router.post("/buy/{tariff_id}")
async def webapp_buy(
    tariff_id: int,
    request: Request,
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Отправляет инвойс пользователю через бота."""
    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None or not tariff.is_active:
        raise HTTPException(status_code=404, detail="tariff_not_found")

    bot: Bot | None = _get_bot(request)
    if bot is None:
        raise HTTPException(status_code=503, detail="bot_unavailable")

    from aiogram.types import LabeledPrice

    user = await users_q.get_user(db, telegram_id)
    price = tariff.price_stars

    if user and user.pending_promo_id:
        pending_promo = await promo_q.get_by_id(db, user.pending_promo_id)
        if pending_promo and pending_promo.code_type == "discount" and promo_q.is_available(pending_promo):
            applies = pending_promo.discount_tariff_id is None or pending_promo.discount_tariff_id == tariff.id
            if applies:
                discount = min(pending_promo.discount_stars or 0, price - 1)
                price = price - discount

    try:
        await bot.send_invoice(
            chat_id=telegram_id,
            title=tariff.name,
            description=tariff.description or f"Подписка «{tariff.name}»",
            payload=f"tariff_{tariff.id}_{telegram_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=tariff.name, amount=price)],
        )
    except Exception as exc:
        logger.exception("Ошибка отправки инвойса user=%s: %s", telegram_id, exc)
        raise HTTPException(status_code=500, detail="invoice_send_failed")

    return {"ok": True, "message": "Инвойс отправлен в ваш чат с ботом"}


@router.post("/activate")
async def webapp_activate(
    body: ActivateRequest,
    request: Request,
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    code = body.code.strip()
    promo = await promo_q.get_by_code(db, code)
    if promo is None:
        raise HTTPException(status_code=404, detail="code_not_found")
    if not promo_q.is_available(promo):
        raise HTTPException(status_code=409, detail="code_used_or_expired")

    user = await users_q.get_user(db, telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    if promo.code_type == "discount":
        await users_q.set_pending_promo(db, telegram_id, promo.id)
        return {"type": "discount", "message": f"Скидка −{promo.discount_stars}⭐ применена к следующей покупке"}

    # Access code
    access_expires = await sub_service.activate_promo(db, user, promo)
    await promo_q.record_use(db, promo, telegram_id, access_expires)

    bot: Bot | None = _get_bot(request)
    if bot:
        period = "навсегда" if promo.duration_days is None else f"до {access_expires.strftime('%d.%m.%Y') if access_expires else '?'}"
        try:
            await bot.send_message(telegram_id, f"✅ <b>Подписка активирована!</b> Доступ открыт {period}.")
        except Exception:  # noqa: BLE001
            pass

    expires_at = access_expires.isoformat() if access_expires else None
    return {"type": "access", "message": "Подписка активирована!", "expires_at": expires_at}


_CONNECT_PHOTO_PATH = BASE_DIR / "connecting_bot_photo" / "connecting_bot.jpg"


@router.get("/instruction-photo", dependencies=[Depends(_require_webapp_auth)])
async def webapp_instruction_photo(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Отдаёт фото инструкции по подключению (публично для авторизованных пользователей)."""
    # Сначала ищем закешированный file_id → local_path через MediaCache
    cached_fid = await settings_q.get_setting(db, "connect_photo_file_id")
    if cached_fid:
        cache_row = await db.execute(
            select(MediaCache).where(MediaCache.file_id == cached_fid)
        )
        cache = cache_row.scalar_one_or_none()
        if cache and cache.local_path:
            path = Path(cache.local_path)
            if path.exists():
                etag = cache.content_hash or cache.file_unique_id
                if request.headers.get("if-none-match") == etag:
                    return Response(status_code=304)
                return FileResponse(str(path), media_type="image/jpeg",
                                    headers={"ETag": etag, "Cache-Control": "public, max-age=86400"})

    # Fallback — файл на диске
    if _CONNECT_PHOTO_PATH.exists():
        return FileResponse(str(_CONNECT_PHOTO_PATH), media_type="image/jpeg",
                            headers={"Cache-Control": "public, max-age=86400"})

    raise HTTPException(status_code=404, detail="instruction_photo_not_found")


_MEDIA_MIME: dict[str, str] = {
    "photo": "image/jpeg",
    "video": "video/mp4",
    "audio": "audio/mpeg",
    "voice": "audio/ogg",
    "video_note": "video/mp4",
    "sticker": "image/webp",
    "animation": "video/mp4",
    "document": "application/octet-stream",
}


@router.get("/media/{file_unique_id}")
async def webapp_media(
    request: Request,
    file_unique_id: str,
    telegram_id: int = Depends(_require_webapp_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Отдаёт медиафайл пользователю — только его собственные сообщения."""
    # Проверяем что файл принадлежит этому пользователю
    owner_check = await db.execute(
        select(MessageLog.id).where(
            MessageLog.file_unique_id == file_unique_id,
            MessageLog.user_id == telegram_id,
        ).limit(1)
    )
    if owner_check.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="not_found")

    cache_row = await db.execute(
        select(MediaCache).where(MediaCache.file_unique_id == file_unique_id)
    )
    cache = cache_row.scalar_one_or_none()

    if cache is None or not cache.local_path:
        raise HTTPException(status_code=404, detail="not_cached")

    path = Path(cache.local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file_deleted")

    etag = cache.content_hash or file_unique_id
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)

    mime = mimetypes.guess_type(path.name)[0] or _MEDIA_MIME.get(cache.file_type or "", "application/octet-stream")

    return FileResponse(
        path=str(path),
        media_type=mime,
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=86400",
            "Accept-Ranges": "bytes",
        },
    )
