# z.ps1 - команды для разработки и деплоя Zynto Bot
# Использование: .\z.ps1 <команда>
param([string]$cmd = "help")

$Root    = $PSScriptRoot
$Python  = "$Root\venv\Scripts\python.exe"
$Server  = "100.73.18.94"   # Tailscale IP
$SshKey  = "C:\Users\user\.ssh\bandana\id_ed25519_newserver"
$SshUser = "user"

# Читаем POSTGRES_PASSWORD из .env для db-reset
function Get-EnvValue([string]$key) {
    $envFile = "$Root\.env"
    if (-not (Test-Path $envFile)) { return $null }
    $line = Get-Content $envFile | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
    if ($line) { return $line.Split("=", 2)[1].Trim() }
    return $null
}

function Run-SSH([string]$script) {
    $script | ssh -tt -i $SshKey -o StrictHostKeyChecking=no -o ConnectTimeout=15 "${SshUser}@${Server}" bash
}

switch ($cmd) {

    # ════════════════════════════════════════════════════════
    # ЛОКАЛЬНАЯ РАЗРАБОТКА
    # ════════════════════════════════════════════════════════

    "bot" {
        # Запуск бота с API (polling)
        Write-Host "Запуск бота..." -ForegroundColor Cyan
        & $Python "$Root\main.py"
    }

    "ui" {
        # Miniapp dev server → http://localhost:5173/miniapp/
        Write-Host "Miniapp dev server → http://localhost:5173/miniapp/" -ForegroundColor Cyan
        Set-Location "$Root\miniapp"
        npm run dev
    }

    "build-ui" {
        # Собрать miniapp → static/miniapp/ (нужно перед деплоем)
        Write-Host "Сборка miniapp → static/miniapp..." -ForegroundColor Cyan
        Set-Location "$Root\miniapp"
        npm run build
        Set-Location $Root
        Write-Host "Готово." -ForegroundColor Green
    }

    "migrate" {
        # Применить Alembic миграции локально
        Write-Host "Применяю миграции..." -ForegroundColor Cyan
        Set-Location $Root
        & $Python -m alembic upgrade head
    }

    "db-reset" {
        # Пересоздать локальную БД с нуля и прогнать все миграции
        Write-Host "Пересоздаю БД tgguard..." -ForegroundColor Yellow
        $pgPass = Get-EnvValue "POSTGRES_PASSWORD"
        $psql = (Get-ChildItem "C:\Program Files\PostgreSQL" -Recurse -Filter "psql.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
        if (-not $psql) {
            Write-Host "psql не найден. Укажи путь вручную или запусти из pgAdmin." -ForegroundColor Red
            return
        }
        $env:PGPASSWORD = $pgPass
        & $psql -U postgres -h localhost -c "DROP DATABASE IF EXISTS tgguard;" -c "CREATE DATABASE tgguard;"
        $env:PGPASSWORD = $null
        Write-Host "Применяю миграции..." -ForegroundColor Cyan
        Set-Location $Root
        & $Python -m alembic upgrade head
        Write-Host ""
        Write-Host "Готово. Теперь:" -ForegroundColor Green
        Write-Host "  1. .\z.ps1 bot       — запусти бота"
        Write-Host "  2. Напиши /start боту в Telegram — создаст пользователя в БД"
        Write-Host "  3. .\z.ps1 ui        — открой miniapp в браузере"
    }

    "logs" {
        # Tail локального лог-файла
        Get-Content "$Root\logs\bot.log" -Wait -Tail 60
    }

    "syntax" {
        # Проверка синтаксиса Python (без venv)
        & $Python -m compileall -q "$Root" -x "venv|__pycache__"
    }

    # ════════════════════════════════════════════════════════
    # ДЕПЛОЙ НА СЕРВЕР
    # ════════════════════════════════════════════════════════

    "deploy" {
        # Полный деплой: build ui → git push → pull на сервере → docker rebuild → логи

        Write-Host ""
        Write-Host "[1/4] Сборка miniapp..." -ForegroundColor Cyan
        Set-Location "$Root\miniapp"
        npm run build
        if ($LASTEXITCODE -ne 0) { Write-Host "Сборка упала" -ForegroundColor Red; return }
        Set-Location $Root

        Write-Host "[2/4] git push..." -ForegroundColor Cyan
        git add static/
        $status = git status --porcelain
        if ($status) {
            git commit -m "build: update static miniapp"
        }
        git push origin main
        if ($LASTEXITCODE -ne 0) { Write-Host "git push упал" -ForegroundColor Red; return }

        Write-Host "[3/4] Деплой на сервер ($Server)..." -ForegroundColor Cyan
        $deployScript = @'
set -e
cd ~/zynto-bot

echo "--- git pull ---"
if [ ! -f ~/.git_pat ]; then
  echo "ОШИБКА: файл ~/.git_pat не найден на сервере."
  echo "Создай его: echo 'ТВОЙ_GITHUB_PAT' > ~/.git_pat && chmod 600 ~/.git_pat"
  exit 1
fi
printf '#!/bin/sh\ncase "$1" in\n  User*) echo Lipsii ;;\n  Pass*) cat ~/.git_pat ;;\nesac\n' > /tmp/askpass.sh
chmod +x /tmp/askpass.sh
GIT_ASKPASS=/tmp/askpass.sh git pull
rm -f /tmp/askpass.sh

echo "--- docker build & restart ---"
docker compose up -d --build

echo "--- миграции ---"
sleep 3
docker compose exec bot python -m alembic upgrade head || true

echo "--- деплой завершён ---"
'@
        Run-SSH $deployScript
        if ($LASTEXITCODE -ne 0) { Write-Host "Деплой упал" -ForegroundColor Red; return }

        Write-Host "[4/4] Последние логи..." -ForegroundColor Cyan
        Run-SSH "cd ~/zynto-bot && docker compose logs --tail=30 bot"
    }

    "push" {
        # Только git push (без build ui и деплоя на сервер)
        Write-Host "git push origin main..." -ForegroundColor Cyan
        git push origin main
    }

    "ssh" {
        # SSH на сервер
        Write-Host "Подключение к $Server через Tailscale..." -ForegroundColor Cyan
        ssh -tt -i $SshKey -o StrictHostKeyChecking=no -o ConnectTimeout=15 "${SshUser}@${Server}"
    }

    "server-logs" {
        # Логи бота в реальном времени
        Run-SSH "cd ~/zynto-bot && docker compose logs -f --tail=50 bot"
    }

    "server-migrate" {
        # Применить миграции на сервере (бот должен быть запущен)
        Run-SSH "cd ~/zynto-bot && docker compose exec bot python -m alembic upgrade head"
    }

    "server-restart" {
        # Перезапустить контейнер бота без rebuild
        Run-SSH "cd ~/zynto-bot && docker compose restart bot"
    }

    "server-status" {
        # Статус контейнеров + последние логи
        Run-SSH "cd ~/zynto-bot && docker compose ps && echo '' && docker compose logs --tail=20 bot"
    }

    "server-update-pat" {
        # Обновить GitHub PAT на сервере
        $pat = Read-Host "Введи новый GitHub PAT"
        if (-not $pat) { Write-Host "PAT не введён" -ForegroundColor Red; return }
        Run-SSH "echo '$pat' > ~/.git_pat && chmod 600 ~/.git_pat && echo 'PAT обновлён'"
    }

    # ════════════════════════════════════════════════════════
    # HELP
    # ════════════════════════════════════════════════════════

    default {
        Write-Host ""
        Write-Host "  Zynto Bot — команды (.\z.ps1 <команда>)" -ForegroundColor White
        Write-Host ""
        Write-Host "  ЛОКАЛЬНО:" -ForegroundColor Yellow
        Write-Host "  bot              запустить бота (polling + REST API на :8000)"
        Write-Host "  ui               miniapp dev server → http://localhost:5173/miniapp/"
        Write-Host "  migrate          применить Alembic миграции"
        Write-Host "  db-reset         пересоздать БД с нуля + все миграции"
        Write-Host "  logs             tail logs/bot.log"
        Write-Host "  build-ui         собрать miniapp → static/miniapp/ (без деплоя)"
        Write-Host "  syntax           проверить синтаксис Python"
        Write-Host ""
        Write-Host "  СЕРВЕР:" -ForegroundColor Yellow
        Write-Host "  deploy           build ui + git push + pull + docker rebuild + логи"
        Write-Host "  push             только git push (без build и деплоя)"
        Write-Host "  ssh              SSH на сервер (через Tailscale)"
        Write-Host "  server-logs      логи бота в реальном времени"
        Write-Host "  server-migrate   применить миграции на сервере"
        Write-Host "  server-restart   перезапустить контейнер бота"
        Write-Host "  server-status    статус контейнеров + последние логи"
        Write-Host "  server-update-pat  обновить GitHub PAT на сервере"
        Write-Host ""
        Write-Host "  Первый запуск локально:" -ForegroundColor DarkGray
        Write-Host "  1. .\z.ps1 db-reset   # пересоздать БД"
        Write-Host "  2. .\z.ps1 bot        # запустить бота (терминал 1)"
        Write-Host "  3. Написать /start боту в Telegram"
        Write-Host "  4. .\z.ps1 ui         # miniapp (терминал 2)"
        Write-Host ""
    }
}
