"""Помощники для пагинации."""
from __future__ import annotations

from dataclasses import dataclass

PAGE_SIZE = 10


@dataclass
class Page:
    offset: int
    limit: int
    page: int
    total_pages: int

    @property
    def has_prev(self) -> bool:
        return self.page > 0

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages - 1


def make_page(page: int, total_items: int, page_size: int = PAGE_SIZE) -> Page:
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    return Page(offset=page * page_size, limit=page_size, page=page, total_pages=total_pages)
