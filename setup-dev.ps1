# setup-dev.ps1 — регистрирует команду `z` в PowerShell профиле
# Запусти один раз: .\setup-dev.ps1
# После этого в любом терминале: z bot, z deploy, z help и т.д.

$ProjectRoot = $PSScriptRoot
$FunctionDef = @"

# Zynto Bot dev commands
function z { & "$ProjectRoot\z.ps1" `@args }
"@

# Создать профиль если не существует
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Host "Создан PowerShell профиль: $PROFILE" -ForegroundColor Gray
}

# Проверить не добавлена ли уже функция
$profileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($profileContent -and $profileContent -match "Zynto Bot dev commands") {
    # Обновить путь (на случай если проект переехал)
    $updated = $profileContent -replace "function z \{ & `".*?z\.ps1`" @args \}", "function z { & `"$ProjectRoot\z.ps1`" @args }"
    Set-Content $PROFILE $updated
    Write-Host "Команда z уже есть в профиле — путь обновлён." -ForegroundColor Yellow
} else {
    Add-Content $PROFILE $FunctionDef
    Write-Host "Команда z добавлена в профиль." -ForegroundColor Green
}

Write-Host ""
Write-Host "Применить прямо сейчас (без перезапуска терминала):" -ForegroundColor Cyan
Write-Host "  . `$PROFILE"
Write-Host ""
Write-Host "Или просто открой новый терминал и используй:" -ForegroundColor Cyan
Write-Host "  z help"
Write-Host "  z bot"
Write-Host "  z deploy"
