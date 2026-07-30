"""CRUD тарифов."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription, Tariff

# Лимит Telegram Bot API на инвойс в XTR (Stars): 1–10000. Цена выше сохранится
# в БД, но send_invoice упадёт — валидируем на всех точках записи.
MAX_PRICE_STARS = 10_000


async def get_tariff(db: AsyncSession, tariff_id: int) -> Tariff | None:
    res = await db.execute(select(Tariff).where(Tariff.id == tariff_id))
    return res.scalar_one_or_none()


async def list_tariffs(db: AsyncSession, only_active: bool = True) -> list[Tariff]:
    stmt = select(Tariff)
    if only_active:
        stmt = stmt.where(Tariff.is_active == True)  # noqa: E712
    stmt = stmt.order_by(Tariff.sort_order, Tariff.price_stars)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_tariff(
    db: AsyncSession,
    name: str,
    description: str | None,
    duration_days: int | None,
    price_stars: int,
    sort_order: int,
    created_by: int,
) -> Tariff:
    tariff = Tariff(
        name=name,
        description=description,
        duration_days=duration_days,
        price_stars=price_stars,
        sort_order=sort_order,
        created_by=created_by,
    )
    db.add(tariff)
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def update_tariff(db: AsyncSession, tariff_id: int, **fields) -> Tariff | None:
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(tariff, key):
            setattr(tariff, key, value)
    await db.commit()
    await db.refresh(tariff)
    return tariff


def price_locked_by_sale(tariff: Tariff) -> bool:
    """True, если у тарифа активна акция (`original_price_stars` заполнен) —
    в этом случае `price_stars` является акционной ценой и не должен меняться
    напрямую через обычный PATCH/редактирование, только через `start_sale`
    (скорректировать акцию) или `end_sale` (сначала снять акцию)."""
    return tariff.original_price_stars is not None


async def update_tariff_fields(db: AsyncSession, tariff_id: int, fields: dict) -> Tariff | None:
    """Частичное обновление, в отличие от `update_tariff` не пропускает явный None.

    Нужно, чтобы `duration_days=None` (вечный тариф) можно было выставить через
    PATCH-эндпоинт мини-аппа — `update_tariff(**fields)` игнорирует None-значения.
    Вызывающий код должен передавать только реально присланные клиентом поля
    (например `body.model_dump(exclude_unset=True)`).

    Returns:
        None — тариф не найден (сохраняем прежний контракт для вызывающего
        кода, которое отвечает на это 404).

    Raises:
        ValueError("price_locked_by_sale") — попытка напрямую изменить
            `price_stars` при активной акции (см. `price_locked_by_sale()`).
            Это единственное поле, для которого во время акции обязателен
            путь через `start_sale`/`end_sale` — иначе `discount_percent()`
            считается от «неправильной» базы и может уйти в 0/отрицательное
            значение.
    """
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        return None
    if "price_stars" in fields and price_locked_by_sale(tariff):
        raise ValueError("price_locked_by_sale")
    for key, value in fields.items():
        if hasattr(tariff, key):
            setattr(tariff, key, value)
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def toggle_tariff(db: AsyncSession, tariff_id: int) -> Tariff | None:
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        return None
    tariff.is_active = not tariff.is_active
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def count_subscriptions_for_tariff(db: AsyncSession, tariff_id: int) -> int:
    res = await db.execute(
        select(func.count(Subscription.id)).where(Subscription.tariff_id == tariff_id)
    )
    return int(res.scalar() or 0)


def discount_percent(tariff: Tariff) -> int | None:
    """Процент скидки для отдачи в API/чате — считается на лету, не хранится в БД.
    None, если акции нет (original_price_stars пуст).

    Defense-in-depth: при корректной работе `start_sale`/`end_sale` и защите в
    `update_tariff_fields` результат всегда > 0, но если данные в БД всё же
    оказались в противоречивом состоянии (price_stars >= original_price_stars),
    отдаём None вместо 0/отрицательного числа — чтобы клиенты (бот, мини-апп)
    показывали тариф как обычный, без сломанного бейджа акции."""
    if not tariff.original_price_stars:
        return None
    percent = round((1 - tariff.price_stars / tariff.original_price_stars) * 100)
    return percent if percent > 0 else None


async def start_sale(db: AsyncSession, tariff_id: int, new_price_stars: int) -> Tariff:
    """Запускает или обновляет акцию на тариф.

    Первый вызов (акции ещё нет): текущая `price_stars` копируется в
    `original_price_stars`, затем `price_stars` заменяется на `new_price_stars`.
    Повторный вызов при уже активной акции: `original_price_stars` не трогается
    (это «настоящая» базовая цена), меняется только акционная `price_stars` —
    так админ может скорректировать размер скидки, не теряя точку отсчёта.

    `new_price_stars` валидируется здесь (а не только на API-уровне), т.к. это
    единственное место в проекте, где разрешено менять цену тарифа во время
    акции — прямой PATCH её не трогает.

    Raises:
        ValueError("tariff_not_found") — тариф не найден.
        ValueError("invalid_price") — не целое положительное число в пределах
            лимита Bot API (см. MAX_PRICE_STARS).
        ValueError("price_not_lower") — новая цена не меньше базовой (либо
            уже сохранённой original_price_stars, либо текущей price_stars,
            если акции ещё не было) — акция обязана быть скидкой, не наценкой.
    """
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        raise ValueError("tariff_not_found")
    if not isinstance(new_price_stars, int) or not (1 <= new_price_stars <= MAX_PRICE_STARS):
        raise ValueError("invalid_price")
    base_price = tariff.original_price_stars if tariff.original_price_stars is not None else tariff.price_stars
    if new_price_stars >= base_price:
        raise ValueError("price_not_lower")
    if tariff.original_price_stars is None:
        tariff.original_price_stars = tariff.price_stars
    tariff.price_stars = new_price_stars
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def end_sale(db: AsyncSession, tariff_id: int) -> Tariff:
    """Завершает акцию: восстанавливает `price_stars = original_price_stars`
    и обнуляет `original_price_stars`.

    Raises:
        ValueError("tariff_not_found") — тариф не найден.
        ValueError("no_active_sale") — акции на тарифе сейчас нет.
    """
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        raise ValueError("tariff_not_found")
    if tariff.original_price_stars is None:
        raise ValueError("no_active_sale")
    tariff.price_stars = tariff.original_price_stars
    tariff.original_price_stars = None
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def delete_tariff(db: AsyncSession, tariff_id: int) -> bool:
    """Удаляет тариф даже при наличии подписок: история хранит tariff_id без FK
    и обратно его не резолвит — «висячий» id безопасен. Оплата уже отправленного
    инвойса на удалённый тариф отбивается в handlers/user/subscription.py
    (tariff is None → предупреждение пользователю)."""
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        return False
    await db.delete(tariff)
    await db.commit()
    return True
