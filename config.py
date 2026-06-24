"""Загрузка конфигурации из .env и класс Settings."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    superadmin_id: int = field(default_factory=lambda: _get_int("SUPERADMIN_ID", 0))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    storage_type: str = field(default_factory=lambda: os.getenv("STORAGE_TYPE", "local"))
    media_path: Path = field(default_factory=lambda: (BASE_DIR / os.getenv("MEDIA_PATH", "./media")).resolve())

    s3_endpoint: str = field(default_factory=lambda: os.getenv("S3_ENDPOINT", ""))
    s3_access_key: str = field(default_factory=lambda: os.getenv("S3_ACCESS_KEY", ""))
    s3_secret_key: str = field(default_factory=lambda: os.getenv("S3_SECRET_KEY", ""))
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", ""))

    max_file_size_mb: int = field(default_factory=lambda: _get_int("MAX_FILE_SIZE_MB", 50))
    text_retention_days: int = field(default_factory=lambda: _get_int("TEXT_RETENTION_DAYS", 90))
    media_retention_days: int = field(default_factory=lambda: _get_int("MEDIA_RETENTION_DAYS", 30))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def logs_dir(self) -> Path:
        return BASE_DIR / "logs"

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN не задан в .env")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL не задан в .env")


settings = Settings()
