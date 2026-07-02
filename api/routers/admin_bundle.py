"""GET /webapp/modules/core — бандл admin-раздела мини-аппа (JS+CSS), только для админов.

Не раздаётся как статика: файлы static/miniapp-admin/ намеренно НЕ примонтированы
в /assets или /miniapp/assets — доступ только через этот роутер за require_webapp_admin.
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from api.deps import require_webapp_admin
from config import BASE_DIR

router = APIRouter(prefix="/webapp/modules", tags=["webapp-admin"])

_ADMIN_DIST = BASE_DIR / "static" / "miniapp-admin"


@router.get("/core")
async def admin_module(
    request: Request,
    telegram_id: int = Depends(require_webapp_admin),
) -> Response:
    js_path = _ADMIN_DIST / "entry.js"
    css_path = _ADMIN_DIST / "entry.css"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="Not Found")

    css_bytes = css_path.read_bytes() if css_path.exists() else b""
    digest = hashlib.sha256(js_path.read_bytes() + css_bytes).hexdigest()
    if request.headers.get("if-none-match") == digest:
        return Response(status_code=304)

    payload = {
        "js": js_path.read_text("utf-8"),
        "css": css_path.read_text("utf-8") if css_path.exists() else "",
    }
    return JSONResponse(
        payload,
        headers={"ETag": digest, "Cache-Control": "private, no-store"},
    )
