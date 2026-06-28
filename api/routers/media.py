"""GET /media/:fileUniqueId — скачивание файла с ETag-кешированием."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_auth
from database.queries.media import get_by_unique_id

router = APIRouter(prefix="/media", tags=["media"], dependencies=[Depends(require_auth)])

# file_type в media_cache — "photo", "video", etc. Маппим в базовый MIME для отдачи.
_TYPE_MIME: dict[str, str] = {
    "photo": "image/jpeg",
    "video": "video/mp4",
    "audio": "audio/mpeg",
    "voice": "audio/ogg",
    "video_note": "video/mp4",
    "sticker": "image/webp",
    "animation": "video/mp4",
    "document": "application/octet-stream",
}


@router.get("/{file_unique_id}")
async def download_media(
    request: Request,
    file_unique_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    cache = await get_by_unique_id(db, file_unique_id)

    if cache is None or not cache.local_path:
        return Response(
            status_code=404,
            content='{"error":"not_found","message":"Файл не скачан или удалён"}',
            media_type="application/json",
        )

    path = Path(cache.local_path)
    if not path.exists():
        # Файл удалён с диска (cleaner успел, БД ещё не обновлена)
        return Response(
            status_code=404,
            content='{"error":"not_found","message":"Файл удалён с диска"}',
            media_type="application/json",
        )

    etag = cache.content_hash or file_unique_id
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)

    # MIME: сначала пробуем угадать по расширению файла, иначе по типу из БД
    mime = mimetypes.guess_type(path.name)[0] or _TYPE_MIME.get(cache.file_type or "", "application/octet-stream")

    return FileResponse(
        path=str(path),
        media_type=mime,
        headers={
            "ETag": etag,
            "Cache-Control": "public, immutable, max-age=31536000",
        },
    )
