"""POST /cache/invalidate — принудительная инвалидация клиентского кеша."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import require_auth
from services import ws_broadcaster as broadcaster

router = APIRouter(prefix="/cache", tags=["cache"], dependencies=[Depends(require_auth)])


class InvalidateRequest(BaseModel):
    scope: str = "all"           # "all" | "messages" | "media" | "users" | "stats"
    resourceId: Optional[str] = None


class InvalidateResponse(BaseModel):
    invalidated: bool
    scope: str
    resourceId: Optional[str]


@router.post("/invalidate", response_model=InvalidateResponse)
async def invalidate_cache(body: InvalidateRequest = InvalidateRequest()) -> InvalidateResponse:
    await broadcaster.broadcast(
        "cache.invalidated",
        {"scope": body.scope, "resourceId": body.resourceId},
    )
    return InvalidateResponse(invalidated=True, scope=body.scope, resourceId=body.resourceId)
