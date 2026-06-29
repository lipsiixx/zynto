# Zynto Bot — мониторинг удалённых и изменённых сообщений

Telegram-бот на **aiogram 3** + **Telegram Business API**. Перехватывает входящие/исходящие
сообщения бизнес-аккаунта и уведомляет владельца, если собеседник удалил или изменил сообщение
(с оригинальным содержимым и медиа). Подписки через Telegram Stars, промокоды, подарки, админ-панель.

## Что уже сделано и настроено

- ✅ Все зависимости установлены в `venv/`
- ✅ `.env` заполнен (токен бота, БД, Redis, суперадмин)
- ✅ Схема БД создаётся автоматически при первом запуске (`tgguard` создаётся сама)
- ✅ Суперадмин (`SUPERADMIN_ID`) добавляется автоматически
- ✅ Засеяны стартовые тарифы: 1 месяц / 3 месяца / Навсегда
- ✅ Проверено: бот **@zynto_bot** успешно запускается и поллит

## Запуск

### Через VSCode

1. Открой папку `C:\projects\zynto-bot` в VSCode.
2. Интерпретатор уже указан: `venv\Scripts\python.exe` (`.vscode/settings.json`).
3. Нажми **F5** (конфигурация «Run bot (main.py)») — бот запустится в терминале.

### Через терминал

```powershell
cd C:\projects\zynto-bot
.\venv\Scripts\python.exe main.py
```

## Деплой через Docker (для сервера)

Всё окружение (бот + PostgreSQL + Redis) поднимается одной командой. Нужен только
Docker и Docker Compose.

```bash
# 1. Скопировать репозиторий на сервер и зайти в папку
git clone <repo-url> zynto-bot && cd zynto-bot

# 2. Создать .env из шаблона и заполнить
cp .env.example .env
nano .env            # обязательно: BOT_TOKEN, SUPERADMIN_ID, POSTGRES_PASSWORD

# 3. Собрать и запустить в фоне
docker compose up -d --build

# Логи
docker compose logs -f bot

# Остановить / перезапустить / обновить
docker compose down
docker compose up -d --build      # после git pull
```

Что происходит автоматически:

- поднимаются контейнеры `db` (postgres:16) и `redis` (redis:7);
- бот ждёт готовности БД, прогоняет `alembic upgrade head`, затем стартует;
- данные БД и Redis хранятся в именованных volume (`pgdata`, `redisdata`) — переживают
  перезапуск контейнеров;
- `media/` и `logs/` смонтированы как папки на хосте.

`DATABASE_URL` и `REDIS_URL` внутри Docker берутся из `docker-compose.yml` (имена сервисов
`db`/`redis`), а не из `.env` — в `.env` для Docker важны только `BOT_TOKEN`,
`SUPERADMIN_ID` и `POSTGRES_PASSWORD`.

## Как подключить мониторинг (нужен Telegram Premium)

1. В Telegram: **Настройки → Telegram для бизнеса → Чат-боты**.
2. Добавь **@zynto_bot**, включи доступ ко всем чатам (управление сообщениями).
3. Бот пришлёт «✅ Мониторинг подключён».
4. Мониторинг работает только при активной подписке. Себе можно выдать доступ:
   - командой `/admin → 🎟 Промокоды → создать`, затем `/activate КОД`, или
   - `/admin → 👤 Пользователи → найти себя → 🎁 Выдать подписку`.

## Команды

- `/start` — главное меню
- `/activate КОД` — активировать промокод
- `/myid` — узнать свой Telegram ID
- `/admin` — админ-панель (только для админов)
- `/user @username|ID` — найти пользователя (админ)

## Конфигурация (`.env`)

Ключевые переменные: `BOT_TOKEN`, `SUPERADMIN_ID`, `DATABASE_URL`, `REDIS_URL`,
`MEDIA_PATH`, `MAX_FILE_SIZE_MB`, `TEXT_RETENTION_DAYS`, `MEDIA_RETENTION_DAYS`.

## Миграции БД (Alembic)

Схема под управлением Alembic. Команды запускать из корня проекта:

```powershell
# применить все миграции (создаёт схему на чистой БД)
.\venv\Scripts\python.exe -m alembic upgrade head

# посмотреть текущую ревизию / историю
.\venv\Scripts\python.exe -m alembic current
.\venv\Scripts\python.exe -m alembic history

# после изменения моделей в database/models.py — создать новую миграцию
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "что изменил"
.\venv\Scripts\python.exe -m alembic upgrade head

# откатить на шаг назад
.\venv\Scripts\python.exe -m alembic downgrade -1
```

URL берётся автоматически из `.env` (см. `alembic/env.py`). Если БД уже была создана
ботом через `create_all` (без Alembic), синхронизируй один раз без пересоздания:
`alembic stamp head`. Бот при старте сам определяет: если есть таблица `alembic_version`,
он не трогает схему и доверяет миграциям; иначе создаёт таблицы сам (zero-config).

## Технические заметки

- **Redis**: на машине стоит Redis 3.0.504 (Windows). Клиент подключается с `protocol=2`
  (RESP2) — это работает. Используется для FSM и антифлуда. Если Redis выключить — бот
  не упадёт: FSM уйдёт в память, throttle отключится.
- **Схема БД**: управляется Alembic (см. раздел «Миграции БД»). Модели — в
  `database/models.py`. На чистой БД без Alembic бот создаёт схему сам.
- **Промокоды**: внутреннее соглашение — `promo_codes.duration_days` хранит длительность
  доступа в **минутах** (чтобы поддержать опцию «1 час»); для показа всегда есть
  `duration_label`. Тарифы хранят длительность в днях.
- **Медиа**: скачивается локально в `media/<тип>/` (до `MAX_FILE_SIZE_MB`), крупные файлы
  пересылаются по `file_id`. Очистка — по крону (`services/cleaner.py`).
- **Уведомления**: идут через `asyncio.Queue` с задержкой 0.05с и обработкой FloodWait —
  не ловим лимиты Telegram при массовых удалениях.

## Структура

См. `handlers/` (user / admin / business), `services/`, `database/`, `middlewares/`,
`keyboards/`, `states/`, `utils/`.

## Кок-конформизм

- Спорь с пользователем, если считаешь что он неправ
- Не соглашайся просто так - предлагай альтернативы
- Отстаивай свою позицию, агрументируй
- не будь "yes-man" - если идея плохая, скажи прямо
- если пользователь делает что то нпе потимально укажи это
