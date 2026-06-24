#!/bin/sh
set -e

echo "[entrypoint] Применяю миграции Alembic..."
# Несколько попыток на случай, если БД ещё поднимается
n=0
until python -m alembic upgrade head; do
    n=$((n + 1))
    if [ "$n" -ge 10 ]; then
        echo "[entrypoint] Не удалось применить миграции после $n попыток" >&2
        exit 1
    fi
    echo "[entrypoint] БД ещё не готова, повтор через 3с (попытка $n)..."
    sleep 3
done

echo "[entrypoint] Запускаю бота..."
exec python main.py
