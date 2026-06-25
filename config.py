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


def _normalize_proxy(raw: str) -> str:
    """Приводит строку прокси к URL вида socks5://user:pass@host:port.

    Принимает:
      - готовый URL:      socks5://user:pass@host:port  (или http://...)
      - формат провайдера: host:port:user:pass
      - без авторизации:   host:port
    Пустые строки и комментарии (#) игнорируются.
    """
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return ""
    if "://" in raw:
        return raw
    parts = raw.split(":")
    if len(parts) == 4:
        host, port, user, pwd = parts
        return f"socks5://{user}:{pwd}@{host}:{port}"
    if len(parts) == 2:
        host, port = parts
        return f"socks5://{host}:{port}"
    return ""


def _load_proxies() -> list[str]:
    """Список прокси: env TELEGRAM_PROXY (один) приоритетнее, иначе все строки proxies.txt."""
    env = os.getenv("TELEGRAM_PROXY", "").strip()
    if env:
        url = _normalize_proxy(env)
        return [url] if url else []
    path = BASE_DIR / "proxies.txt"
    out: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            url = _normalize_proxy(line)
            if url:
                out.append(url)
    return out


def mask_proxy(url: str) -> str:
    """Маскирует пароль в URL прокси для логов."""
    import re
    return re.sub(r"://([^:/]+):[^@]+@", r"://\1:***@", url)


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
    log_retention_days: int = field(default_factory=lambda: _get_int("LOG_RETENTION_DAYS", 14))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # SOCKS5/HTTP-прокси для обхода блокировки Telegram. Источник: env TELEGRAM_PROXY
    # или файл proxies.txt (все строки). Бот при старте выбирает первый рабочий.
    # Пусто — прямое соединение.
    telegram_proxies: list[str] = field(default_factory=_load_proxies)

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def logs_dir(self) -> Path:
        return BASE_DIR / "logs"

    @property
    def telegram_proxy(self) -> str:
        """Первый прокси из списка (или пусто)."""
        return self.telegram_proxies[0] if self.telegram_proxies else ""

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN не задан в .env")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL не задан в .env")


settings = Settings()
