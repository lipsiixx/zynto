# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Telegram-бот (@zynto_bot) на **aiogram 3** / Python 3.12. Перехватывает удалённые и изменённые сообщения бизнес-аккаунта через **Telegram Business API**. Монетизация: Stars (XTR), промокоды, подарки. Многоуровневая админ-панель с FastAPI REST API и WebSocket.

## Команды

```powershell
.\venv\Scripts\python.exe main.py                      # запуск polling
.\venv\Scripts\python.exe -m compileall -q .           # синтаксис (без venv)
.\venv\Scripts\python.exe -m alembic upgrade head      # применить миграции
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "описание"  # новая миграция
```

- **Один polling на токен** — убедись что другой процесс не висит перед запуском.
- Redis — старый **3.0.504**, подключаться с `protocol=2` (RESP3 не поддерживается).
- `TEST=true` в `.env` → прокси пропускаются, прямое соединение (локальная разработка).
- Логи: `logs/bot.log` (UTF-8, RotatingFileHandler 10 МБ × 5).
- Прокси: `proxies.txt` (по одному на строку) или `TELEGRAM_PROXY` в `.env`. Бот при старте перебирает список и берёт первый рабочий.

## Архитектура

### Точка входа — `main.py`

Порядок инициализации: `init_db` → `seed_data` → Redis → прокси-сессия → Bot/Dispatcher → Notifier → ProxyMonitor → роутеры → middlewares → APScheduler → API-сервер → polling.

Порядок включения роутеров в Dispatcher: **business → admin → user** (важно для приоритета).

### Слои

| Слой | Путь | Правило |
|------|------|---------|
| Хендлеры | `handlers/{user,admin,business}/` | Только I/O и вызовы `queries/`. SQL в хендлерах запрещён. |
| Запросы к БД | `database/queries/*.py` | Единственное место с SQLAlchemy-запросами. |
| Модели | `database/models.py` | Источник истины для Alembic. |
| Сервисы | `services/` | Фоновая логика, не привязанная к апдейтам. |
| API | `api/` | FastAPI, запускается в том же event loop, что и бот (`asyncio.create_task`). |
| Состояния FSM | `states/` | `admin_states.py`, `user_states.py`. |

### Middlewares (порядок применения)

1. `DatabaseMiddleware` — outer, все апдейты → добавляет `db` (AsyncSession) в `data`.
2. `AuthMiddleware` — только user-роутер → `get_or_create_user`, проверка бана, истечение подписки → добавляет `user` в `data`.
3. `ThrottleMiddleware` — только user-роутер, Redis, пропускает `successful_payment`.
4. `AdminCheckMiddleware` — только admin-роутер.

**Бизнес-роутер без auth/throttle** — у business-апдейтов нет `from_user`-контекста.

### Планировщик (APScheduler)

| Задача | Интервал | Файл |
|--------|----------|------|
| `cleaner.run_cleanup` | 24 ч | `services/cleaner.py` |
| `check_expired_subscriptions` | 5 мин | `services/subscription.py` |
| `run_nudge_job` | 10 мин | `services/nudge_sender.py` |

### REST API (`api/`)

Запускается только если `API_ENABLED=true` и `API_PASSWORD` задан. Все маршруты под `/v1`. JWT-токены через `api/auth.py`. WebSocket `/v1/ws` и SSE `/v1/events` для real-time событий через `services/ws_broadcaster.py` (fan-out очередь).

SPA: `static/` → `/` (админ-панель), `static/miniapp/` → `/miniapp` (пользовательский мини-апп).

**WebApp API** (`api/routers/webapp.py`) — отдельный роутер `/v1/webapp/*` для мини-аппа. Использует собственный JWT (`create_user_token` / `verify_user_token`), отдельный от admin-токенов. Авторизация через Telegram `initData` (`verify_webapp_init_data`). Ключевые группы эндпоинтов:

| Группа | Пример пути |
|--------|-------------|
| Auth | `POST /webapp/auth`, `GET /webapp/me` |
| Contacts | `GET /webapp/contacts`, `/contacts/{chat_id}/events`, `/contacts/{chat_id}/stats` |
| Mutual Rating | `GET/POST /contacts/{chat_id}/mutual-rating`, `.../accept`, `.../decline`, `DELETE` |
| Trust | `PUT /webapp/trust/{chat_id}` |
| Tariffs/Buy | `GET /webapp/tariffs`, `POST /webapp/buy/{tariff_id}` |
| Promo | `POST /webapp/activate` |
| Referral | `GET /webapp/referral` |
| Network | `GET /webapp/network/status`, `POST /network/join`, `PUT /network/settings`, `GET /network/graph` |
| Media | `GET /webapp/media/{file_unique_id}`, `GET /webapp/instruction-photo` |

### Мини-апп (`miniapp/`)

React 18 + Vite + TypeScript. Структура по **FSD (Feature-Sliced Design)**:

```
src/
  app/        # App.tsx (роутер), AppContext, styles.css
  entities/   # user, contact, message, tariff, referral, network, mutual-rating
  features/   # buy-subscription, activate-promo, mutual-rating, set-trust
  widgets/    # bottom-nav
  pages/      # home, contacts, contact-detail, subscription, activate, referral, network
  shared/     # api/base.ts (HTTP-клиент), ui/Toast
```

**Маршруты** — HashRouter (`#/contacts`, `#/contacts/:chatId`, `#/subscription`, `#/activate`, `#/referral`, `#/network`).

**HTTP-клиент** — `src/shared/api/base.ts`; базовый URL `/v1/webapp`; JWT хранится в `localStorage` (`zynto_token`).

**Dev-режим** — создай `miniapp/.env.local` с `VITE_DEV_USER_ID=<твой_telegram_id>`, тогда при `TEST=true` в `.env` мини-апп будет авторизоваться без реального `initData`.

```powershell
cd miniapp
npm install        # первый раз
npm run dev        # dev-сервер на :5173, /v1 проксируется на localhost:8000
npm run build      # собирает в ../static/miniapp
```

## Критичные инварианты (не ломай)

**Промокоды:** `promo_codes.duration_days` хранит **минуты**, не дни. `duration_label` — для показа. Активация промокода → `timedelta(minutes=...)`. Тарифы хранят дни → `timedelta(days=...)`. Gift конвертирует дни тарифа в минуты. Общее ядро — `grant_access()` в `services/subscription.py`.

**Подписка:** `subscription_status` ∈ `{none, active, lifetime, expired}`. `activate_subscription()` — для тарифов (дни), `activate_promo()` — для промокодов (минуты). Обе идут через `grant_access()`, которая продлевает от текущего `expires_at` если подписка ещё активна.

**Notifier:** глобальная asyncio-очередь (`services/notifier.py`). `MessageLog` живёт между сессиями благодаря `expire_on_commit=False` — не добавляй ленивых relationship к этой модели.

**Throttle:** пропускает `successful_payment` — потеря апдейта оплаты недопустима.

**business_message:** сохраняется каждое (включая исходящие) — иначе нечего показать при удалении. Уведомления только на edit/delete.

**Alembic:** `init_db` уступает Alembic если видит `alembic_version` в БД. Не используй `create_all` напрямую в продакшне.

**Курс:** видео хранится как Telegram `file_id` в `bot_settings` (`course_video_file_id`), не на диске. `course_videos/` — пустая заглушка.

**Nudge:** отправка только в окне 10–21 МСК. Перепланирование (`nudge_next_at`) происходит всегда, даже при ошибке. `TelegramForbiddenError` → `is_blocked=True`. Параметры: `nudge_enabled`, `nudge_grace_days`, `nudge_interval_days` в `bot_settings`.

**cb_connect:** фото с инструкцией отправляется только когда подключение НЕ установлено (единым сообщением: фото + caption + кнопка). Когда активно — только `edit_text`.

**MutualRating:** `requester_id` / `target_id` — это `telegram_id` пользователя, не `user.id`. Пара уникальна по индексу `ix_mutual_rating_pair`. Статусы: `pending|active|declined|cancelled`. При пересоздании после declined/cancelled — старая запись удаляется явно (DELETE), не обновляется.

**ContactTrust:** `manual_score` (0–100) — пользовательский override доверия к контакту. Уникален по `(user_id, chat_id)`. `None` = сброс на автоскор.

**ReferralReward:** лог выданных дней рефереру при оплате реферала. `payment_method` хранит метод оплаты реферала, `days_granted` — фактически начисленные дни.

## .env переменные

| Переменная | Назначение |
|------------|-----------|
| `BOT_TOKEN` | Токен @BotFather |
| `SUPERADMIN_ID` | Telegram ID суперадмина |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `TELEGRAM_PROXY` | SOCKS5/HTTP прокси (один); альтернатива — `proxies.txt` |
| `TEST` | `true` → прокси пропускаются |
| `API_ENABLED` | `true` → запустить FastAPI |
| `API_PASSWORD` | Пароль входа в панель |
| `API_SECRET` | JWT-секрет |
| `API_HOST` / `API_PORT` | Привязка API (default: `0.0.0.0:8000`) |
| `MINIAPP_URL` | URL для кнопки WebApp в боте |
| `STORAGE_TYPE` | `local` или `s3` |
| `TRIBUTE_API_KEY` | HMAC-ключ вебхука Tribute (СБП) |

Колбэки админки — префикс `a:`. Бизнес-роутер — `get_business_router()`.
