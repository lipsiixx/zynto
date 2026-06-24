"""Генерация криптографически случайных промокодов."""
from __future__ import annotations

import secrets
import string

ALPHABET = string.ascii_uppercase + string.digits


def generate_code(length: int = 8) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_gift_code() -> str:
    return f"GIFT-{generate_code(8)}"
