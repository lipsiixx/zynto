"""Скачивание, кеширование и отправка медиафайлов."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import MessageLog
from database.queries import media as media_q

logger = logging.getLogger(__name__)

# Соответствие типа сообщения подпапке и расширению по умолчанию
TYPE_DIR = {
    "photo": ("photos", ".jpg"),
    "video": ("videos", ".mp4"),
    "audio": ("audio", ".mp3"),
    "voice": ("voice", ".ogg"),
    "video_note": ("video_notes", ".mp4"),
    "document": ("documents", ""),
    "sticker": ("stickers", ".webp"),
    "animation": ("videos", ".mp4"),
}


def ensure_media_dirs() -> None:
    for sub, _ in TYPE_DIR.values():
        (settings.media_path / sub).mkdir(parents=True, exist_ok=True)


async def get_or_cache_media(
    bot: Bot,
    db: AsyncSession,
    file_id: str,
    file_unique_id: str,
    file_type: str,
    file_size: int | None,
    mime_type: str | None = None,
) -> str | None:
    """Возвращает local_path если файл скачан, иначе None (используется file_id).

    Логика:
      1. Проверить кеш по file_unique_id.
      2. Если есть local_path и файл существует — вернуть его.
      3. Иначе скачать (если размер позволяет) и сохранить.
    """
    cache = await media_q.get_by_unique_id(db, file_unique_id)
    if cache and cache.local_path and Path(cache.local_path).exists():
        await media_q.touch(db, file_unique_id)
        return cache.local_path

    local_path: str | None = None
    can_download = file_size is None or file_size <= settings.max_file_size_bytes
    if settings.storage_type == "local" and can_download:
        try:
            sub, default_ext = TYPE_DIR.get(file_type, ("documents", ""))
            ext = default_ext
            tg_file = await bot.get_file(file_id)
            if tg_file.file_path:
                src_ext = os.path.splitext(tg_file.file_path)[1]
                if src_ext:
                    ext = src_ext
            dest_dir = settings.media_path / sub
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{file_unique_id}{ext}"
            await bot.download(file_id, destination=dest)
            local_path = str(dest)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось скачать медиа %s: %s", file_unique_id, exc)
            local_path = None

    await media_q.upsert(db, file_unique_id, file_id, file_type, file_size, local_path)
    return local_path


def _input_for(record: MessageLog):
    """Возвращает FSInputFile (если есть локальный файл) или file_id."""
    if record.local_path and Path(record.local_path).exists():
        return FSInputFile(record.local_path)
    return record.file_id


async def send_media(bot: Bot, chat_id: int, record: MessageLog, caption: str) -> bool:
    """Отправляет медиа нужным методом. Возвращает True при успехе."""
    media = _input_for(record)
    if media is None:
        await bot.send_message(chat_id, caption)
        return True

    mtype = record.message_type
    try:
        if mtype == "photo":
            await bot.send_photo(chat_id, media, caption=caption)
        elif mtype == "video":
            await bot.send_video(chat_id, media, caption=caption)
        elif mtype == "audio":
            await bot.send_audio(chat_id, media, caption=caption)
        elif mtype == "voice":
            await bot.send_voice(chat_id, media, caption=caption)
        elif mtype == "video_note":
            await bot.send_video_note(chat_id, media)
            await bot.send_message(chat_id, caption)
        elif mtype == "document":
            await bot.send_document(chat_id, media, caption=caption)
        elif mtype == "sticker":
            await bot.send_sticker(chat_id, media)
            await bot.send_message(chat_id, caption)
        elif mtype == "animation":
            await bot.send_animation(chat_id, media, caption=caption)
        else:
            await bot.send_message(chat_id, caption)
        return True
    except (TelegramBadRequest, FileNotFoundError) as exc:
        logger.warning("Ошибка отправки медиа (%s): %s", mtype, exc)
        await bot.send_message(chat_id, f"{caption}\n\n[{mtype} — файл недоступен]")
        return False
