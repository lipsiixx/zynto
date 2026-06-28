"""GET /chats/:chatId/messages, GET /chats/:chatId/media"""
from __future__ import annotations

import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_auth
from api.schemas import (
    MediaListOut,
    MediaOut,
    MessageCursor,
    MessageOut,
    MessagesListOut,
    Pagination,
)
from database.queries import api as api_q
from database.queries import users as users_q

router = APIRouter(prefix="/chats", tags=["chats"], dependencies=[Depends(require_auth)])


@router.get("/{chat_id}/messages", response_model=MessagesListOut)
async def get_chat_messages(
    request: Request,
    chat_id: int,
    user_id: int = Query(..., description="Внутренний id подписчика (users.id)"),
    before: Optional[int] = Query(None, description="Cursor: id записи (exclusive)"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> MessagesListOut:
    user = await users_q.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, detail="not_found")

    records, has_more = await api_q.list_chat_messages(
        db, user.telegram_id, chat_id, before=before, limit=limit
    )

    data = [MessageOut.from_record(r) for r in records]

    # ETag: хеш от id+receivedAt самого нового сообщения в выдаче
    etag: Optional[str] = None
    if data:
        seed = f"{chat_id}:{data[0].id}:{data[0].receivedAt.isoformat()}"
        etag = hashlib.md5(seed.encode()).hexdigest()

    if etag and request.headers.get("if-none-match") == etag:
        from fastapi.responses import Response
        return Response(status_code=304)  # type: ignore[return-value]

    from fastapi.responses import JSONResponse
    content = MessagesListOut(
        data=data,
        cursor=MessageCursor(
            before=records[-1].id if records else None,
            hasMore=has_more,
        ),
    )
    headers = {"ETag": etag, "Cache-Control": "private, no-store"} if etag else {}
    return JSONResponse(content=content.model_dump(mode="json"), headers=headers)  # type: ignore[return-value]


@router.get("/{chat_id}/media", response_model=MediaListOut)
async def get_chat_media(
    chat_id: int,
    user_id: int = Query(..., description="Внутренний id подписчика"),
    mime_type: Optional[str] = Query(None, description="Фильтр по mimeType, например image/"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> MediaListOut:
    user = await users_q.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, detail="not_found")
    media, total = await api_q.list_chat_media(
        db, user.telegram_id, chat_id, mime_prefix=mime_type, page=page, limit=limit
    )
    return MediaListOut(
        data=[MediaOut(**m) for m in media],
        pagination=Pagination(
            page=page, limit=limit, total=total,
            totalPages=max(1, (total + limit - 1) // limit),
        ),
    )
