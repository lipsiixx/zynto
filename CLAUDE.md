# CLAUDE.md — карта проекта Zynto Bot (читать первым)

> Этот файл — для будущего Claude. Прочитай его прежде чем что-то менять.
> Исходное ТЗ целиком: `план бота.txt` (на русском, очень подробное).

## Что это
Telegram-бот на **aiogram 3** (Python 3.12, venv в `./venv`), который через **Telegram
Business API** перехватывает сообщения бизнес-аккаунта пользователя и уведомляет его, когда
собеседник **удалил** или **изменил** сообщение — показывает оригинал, включая медиа.
Монетизация: подписки за **Telegram Stars (XTR)**, промокоды, подарочные коды. Есть
многоуровневая админ-панель.

Бот зовётся **@zynto_bot**. Premium у владельца обязателен — без него Telegram не шлёт
business-апдейты.

## Как запускать / проверять
```powershell
.\venv\Scripts\python.exe main.py            # запуск бота (polling)
.\venv\Scripts\python.exe -m compileall -q . # быстрая проверка синтаксиса
.\venv\Scripts\python.exe -m alembic upgrade head   # миграции
```
- ВАЖНО: только ОДИН экземпляр polling на токен. Перед своими тест-запусками убедись, что
  не запущен другой процесс (иначе TelegramConflictError).
- Для smoke-теста: запускай через `Start-Process ... -PassThru`, спи ~10с, потом `Stop-Process`.
  Логи пишутся в `logs/bot.log` (UTF-8). В консоли PowerShell кириллица из stderr бьётся
  (cp1251) — это косметика, в файле всё нормально.
- `.env` уже заполнен реальными токеном/БД/паролем. БД: `postgresql+asyncpg://postgres:2300@localhost:5432/tgguard`.
  Redis на :6379 — это **старый Redis 3.0.504**, поэтому подключаемся с `protocol=2` (RESP3/HELLO не поддерживается).

## Архитектура (где что искать)
- `main.py` — точка входа: logging, init_db, seed_data (суперадмин + 3 тарифа), Redis/FSM,
  Notifier, middlewares, роутеры, APScheduler, error handler, polling. `ALLOWED_UPDATES`
  включает business_* апдейты — без них перехват не работает.
- `config.py` — `settings` (dataclass из .env).
- `database/`
  - `engine.py` — async engine, `SessionLocal`, `init_db()` (создаёт саму БД если нет;
    пропускает create_all, если есть таблица `alembic_version`).
  - `models.py` — все SQLAlchemy 2.0 модели. Источник истины для Alembic autogenerate.
  - `queries/*.py` — вся работа с БД, по сущностям (users, admins, tariffs, subscriptions,
    promo_codes, messages, business, media, settings). Хендлеры НЕ пишут SQL напрямую.
- `handlers/`
  - `user/` — start, subscription (+ оплата Stars, pre_checkout, successful_payment),
    activate_code, history, media_gallery, gift, **course** (просмотр видео-курса).
    Собираются в `get_user_router()`.
  - `admin/` — panel, tariffs, promo, stats, server, users_mgmt, admins_mgmt, cleanup,
    **course** (управление курсом: вкл/выкл, загрузка видео, подпись).
    `get_admin_router()`. Колбэки админки имеют префикс `a:`.
  - `business/` — connection, message_handler, edit_handler, delete_handler, extract.
    `get_business_router()`. `resolve_owner()` в message_handler — общий помощник.
- `middlewares/` — database (outer, на dp.update), auth + throttle (inner, на user_router),
  admin_check (inner, на admin_router). Порядок по ТЗ: database → auth → throttle.
- `services/` — subscription (активация/продление/истечение), media (скачивание/кеш/отправка),
  notifier (очередь уведомлений), stats, server_monitor (psutil), cleaner (крон-очистка).
- `keyboards/`, `states/`, `utils/` — клавиатуры, FSM-состояния, форматтеры/пагинация/генератор кодов.
- `course_videos/` — папка-заглушка для локальных видео-файлов курса. Сами видео хранятся
  как Telegram `file_id` в `bot_settings` (ключ `course_video_file_id`). Папка пустая —
  файлы туда НЕ кладутся, она лишь как ориентир для будущего S3/локального хранилища.

## Неочевидные решения (НЕ сломай при правках)
- **Промокоды: `promo_codes.duration_days` хранит МИНУТЫ**, не дни (чтобы поддержать опцию
  «1 час» при integer-схеме). Для показа всегда есть `duration_label`. Активация —
  `services.subscription.activate_promo` (timedelta(minutes=...)). Тарифы же хранят ДНИ и идут
  через `activate_subscription` (timedelta(days=...)). Gift конвертирует дни тарифа в минуты.
  Ядро обоих путей — `grant_access()` (учитывает продление поверх активной подписки).
- **Notifier — отдельная asyncio-очередь** (`services/notifier.py`, глобальный `notifier`).
  Хендлеры удаления/изменения кладут запись в очередь, воркер шлёт с задержкой 0.05с и ловит
  FloodWait/ForbiddenError. Объект `MessageLog` передаётся между сессиями — работает, потому что
  `expire_on_commit=False`; не добавляй ленивых relationship.
- **Throttle пропускает `successful_payment`** — терять апдейт оплаты нельзя.
- **Middleware auth/throttle — inner**, поэтому срабатывают только когда совпал user-хендлер;
  обычные сообщения без хендлера просто проваливаются дальше (это норм).
- **Бизнес-роутер БЕЗ auth/throttle** — у business-апдейтов нет обычного from_user-контекста.
- **Каждое business_message сохраняется** (включая исходящие) — иначе нечего будет показать
  при удалении. Уведомления шлём ТОЛЬКО на edit/delete.
- Схема: и `create_all`, и Alembic. Источник истины — Alembic; `init_db` сам уступает ему.

## Состояние на 2026-06-24
Полностью реализовано по ТЗ и проверено: импорт, compileall, живой запуск (polling стартует,
БД+Redis+scheduler ок), миграция `initial schema` применена. Бот НЕ держится запущенным —
пользователь стартует сам через VSCode (F5, конфиг в `.vscode/`).
Что осознанно НЕ делалось: рефанды Stars (по ТЗ — вручную), S3-хранилище (есть заглушки в
config/media, по умолчанию local).

## Обновления (хронология)

### 2026-06-26 — Видео-курс для пользователей
**Что сделано:** система курса по использованию бота.

**Архитектура курса:**
- Настройки хранятся в `bot_settings` (таблица уже была), три ключа:
  - `course_enabled` — `"0"` / `"1"` (по умолчанию выключен)
  - `course_video_file_id` — Telegram file_id загруженного видео
  - `course_caption` — текст подписи под видео
- Никакой новой таблицы и миграции НЕ требуется — всё через `BotSetting`.
- `database/queries/settings.py` → `ensure_defaults()` дополнен тремя ключами выше.

**Файлы (новые):**
- `handlers/user/course.py` — колбэк `course` (кнопка в меню) + хелпер
  `send_course_after_activation(target, db, bot)` — используется из subscription.py и activate_code.py.
- `handlers/admin/course.py` — колбэки `a:course`, `a:course_toggle`, `a:course_video`,
  `a:course_caption`; FSM-приёмники видео и текста. Роутер подключён в `handlers/admin/__init__.py`.
- `course_videos/.gitkeep` — пустая папка-заглушка (видео хранятся как file_id, не на диске).

**Файлы (изменены):**
- `keyboards/user_kb.py` — кнопка «📚 Курс по использованию» добавлена в `main_menu()`
  (при subscribed=True) и в `main_menu_sub()` (меню после покупки/активации).
- `keyboards/admin_kb.py` — кнопка «📹 Курс для пользователей» в `admin_main()`;
  новая функция `course_kb(is_enabled)`.
- `states/admin_states.py` — добавлен `CourseEditStates` (waiting_video, waiting_caption).
- `handlers/user/subscription.py` — после `on_successful_payment` вызывает
  `send_course_after_activation`.
- `handlers/user/activate_code.py` — `_activate`, `_activate_access`, `cmd_activate`,
  `on_code_entered` получили параметр `bot: Bot`; после активации кода доступа вызывается
  `send_course_after_activation`. Скидочный промокод курс НЕ показывает (это не активация доступа).
- `handlers/user/__init__.py` и `handlers/admin/__init__.py` — подключены новые роутеры.

**Поведение:**
- Курс выключен по умолчанию. Пока видео не загружено — кнопка в меню показывает alert.
- После покупки Stars или активации кода доступа — бот шлёт видео отдельным сообщением
  (если курс включён и видео загружено).
- В меню пользователя кнопка «📚 Курс» всегда видна при наличии подписки.
- Проверено: `compileall -q .` и smoke-запуск (polling стартует без ошибок).
