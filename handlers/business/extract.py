"""Извлечение типа сообщения и медиа-полей из aiogram Message."""
from __future__ import annotations

from dataclasses import dataclass

from aiogram.types import Message


@dataclass
class ExtractedMedia:
    message_type: str
    text_content: str | None = None
    file_id: str | None = None
    file_unique_id: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None


def extract(message: Message) -> ExtractedMedia:
    text = message.text or message.caption

    if message.photo:
        p = message.photo[-1]
        return ExtractedMedia("photo", text, p.file_id, p.file_unique_id, p.file_size, None, None, p.width, p.height)
    if message.video:
        v = message.video
        return ExtractedMedia("video", text, v.file_id, v.file_unique_id, v.file_size, v.mime_type, v.duration, v.width, v.height)
    if message.animation:
        a = message.animation
        return ExtractedMedia("animation", text, a.file_id, a.file_unique_id, a.file_size, a.mime_type, a.duration, a.width, a.height)
    if message.audio:
        a = message.audio
        return ExtractedMedia("audio", text, a.file_id, a.file_unique_id, a.file_size, a.mime_type, a.duration)
    if message.voice:
        v = message.voice
        return ExtractedMedia("voice", text, v.file_id, v.file_unique_id, v.file_size, v.mime_type, v.duration)
    if message.video_note:
        vn = message.video_note
        return ExtractedMedia("video_note", text, vn.file_id, vn.file_unique_id, vn.file_size, None, vn.duration)
    if message.document:
        d = message.document
        return ExtractedMedia("document", text, d.file_id, d.file_unique_id, d.file_size, d.mime_type)
    if message.sticker:
        s = message.sticker
        return ExtractedMedia("sticker", text, s.file_id, s.file_unique_id, s.file_size, None, None, s.width, s.height)
    if message.contact:
        c = message.contact
        return ExtractedMedia("contact", f"{c.first_name or ''} {c.last_name or ''} {c.phone_number or ''}".strip())
    if message.location:
        loc = message.location
        return ExtractedMedia("location", f"{loc.latitude}, {loc.longitude}")
    if message.poll:
        return ExtractedMedia("poll", message.poll.question)
    if message.dice:
        return ExtractedMedia("dice", f"{message.dice.emoji} = {message.dice.value}")
    if getattr(message, "story", None):
        return ExtractedMedia("story", "[история]")

    return ExtractedMedia("text", text)


def chat_title(message: Message) -> str:
    chat = message.chat
    if chat.title:
        return chat.title
    name = " ".join(filter(None, [chat.first_name, chat.last_name]))
    if name:
        return name
    if chat.username:
        return f"@{chat.username}"
    return str(chat.id)
