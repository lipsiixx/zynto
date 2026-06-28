# CLAUDE.md — Zynto Bot

Telegram-бот (@zynto_bot) на **aiogram 3** / Python 3.12. Перехватывает удалённые и изменённые сообщения бизнес-аккаунта через **Telegram Business API**. Монетизация: Stars (XTR), промокоды, подарки. Многоуровневая админ-панель.

## Запуск

```powershell
.\venv\Scripts\python.exe main.py             # polling
.\venv\Scripts\python.exe -m compileall -q .  # синтаксис
.\venv\Scripts\python.exe -m alembic upgrade head  # миграции
```

- **Один polling на токен** — перед запуском убедись что другой процесс не висит.
- Redis — старый **3.0.504**, подключаться с `protocol=2` (RESP3 не поддерживается).
- `TEST=true` в `.env` → прокси пропускаются, прямое соединение (для локальной разработки).
- Логи: `logs/bot.log` (UTF-8). Кириллица в stderr PowerShell бьётся — это косметика.

## Структура

```
main.py           точка входа: init_db, seed_data, Redis, Notifier, роутеры, scheduler, polling
config.py         Settings dataclass из .env
database/
  models.py       все модели SQLAlchemy 2.0 — источник истины для Alembic
  queries/*.py    вся работа с БД; хендлеры SQL не пишут
handlers/
  user/           start, subscription, activate_code, history, media_gallery, gift, course
  admin/          panel, tariffs, promo, stats, server, users_mgmt, admins_mgmt, nudge, course
  business/       connection, message_handler, edit_handler, delete_handler
services/         subscription, media, notifier, nudge_sender, proxy_monitor, cleaner
```

Колбэки админки — префикс `a:`. Бизнес-роутер — `get_business_router()`.

## Критичные инварианты (не ломай)

**Промокоды:** `promo_codes.duration_days` хранит **минуты**, не дни. `duration_label` — для показа. Активация промокода → `timedelta(minutes=...)`. Тарифы хранят дни → `timedelta(days=...)`. Gift конвертирует дни тарифа в минуты. Общее ядро — `grant_access()`.

**Notifier:** глобальная asyncio-очередь (`services/notifier.py`). `MessageLog` живёт между сессиями благодаря `expire_on_commit=False` — не добавляй ленивых relationship.

**Throttle:** пропускает `successful_payment` — терять апдейт оплаты нельзя.

**Бизнес-роутер:** без auth/throttle — у business-апдейтов нет `from_user`-контекста.

**business_message:** сохраняется каждое (включая исходящие) — иначе нечего показать при удалении. Уведомления только на edit/delete.

**Alembic:** источник истины для схемы; `init_db` уступает ему если видит `alembic_version`.

**Курс:** видео хранится как Telegram `file_id` в `bot_settings` (`course_video_file_id`), не на диске. `course_videos/` — пустая заглушка.

**Nudge:** отправка только в окне 10–21 МСК. Перепланирование (`nudge_next_at`) происходит всегда, даже при ошибке отправки. `TelegramForbiddenError` → `is_blocked=True`. Параметры: `nudge_enabled`, `nudge_grace_days`, `nudge_interval_days` в `bot_settings`.

**cb_connect:** фото с инструкцией отправляется только когда подключение НЕ установлено (единым сообщением: фото + caption + кнопка). Когда активно — только edit_text.
