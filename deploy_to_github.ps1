# Разворачивает монитор авиабилетов в GitHub Actions (облако, работа 24/7).
#
# Что делает:
#   1. Проверяет, что установлен GitHub CLI (gh) и выполнен вход.
#   2. Инициализирует git-репозиторий и делает коммит кода.
#   3. Создаёт репозиторий на вашем GitHub и загружает код.
#   4. Переносит ключи из локального .env в зашифрованные секреты GitHub.
#
# ВАЖНО про безопасность:
#   - .env НЕ загружается в репозиторий (он в .gitignore).
#   - Ключи читаются из .env на ВАШЕЙ машине и уходят прямо в секреты GitHub.
#   - Значения ключей скрипт на экран не выводит.
#
# Запуск (из папки проекта):
#   powershell -ExecutionPolicy Bypass -File .\deploy_to_github.ps1
# Необязательные параметры:
#   -RepoName tickets-monitor   -Visibility public   (или private)

param(
    [string]$RepoName = "tickets-monitor",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== Развёртывание монитора в GitHub Actions ==" -ForegroundColor Cyan

# --- 0. Проверки ---------------------------------------------------------
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI (gh) не установлен." -ForegroundColor Red
    Write-Host "Установите: winget install --id GitHub.cli   (затем перезапустите терминал)"
    exit 1
}
try {
    gh auth status 1>$null 2>$null
} catch {
    Write-Host "Вы не вошли в GitHub CLI. Выполните: gh auth login" -ForegroundColor Red
    Write-Host "При входе разрешите доступ к 'workflow' (нужно для загрузки Actions)."
    exit 1
}
if (-not (Test-Path ".env")) {
    Write-Host "Не найден файл .env с ключами. Создайте его из .env.example." -ForegroundColor Red
    exit 1
}

# --- 1. git-репозиторий --------------------------------------------------
if (-not (Test-Path ".git")) {
    git init -b main | Out-Null
}
# локальный автор коммитов, если глобальный не задан
if (-not (git config user.email)) {
    git config user.email "ticket-monitor@local"
    git config user.name  "ticket Monitor"
}
git add -A
git commit -m "Монитор авиабилетов из Екатеринбурга" 2>$null | Out-Null

# --- 2. Создать репозиторий и загрузить код ------------------------------
$hasOrigin = $false
try { git remote get-url origin 1>$null 2>$null; $hasOrigin = $true } catch {}
if ($hasOrigin) {
    Write-Host "Remote 'origin' уже настроен — просто загружаю изменения..."
    git push -u origin main
} else {
    Write-Host "Создаю репозиторий '$RepoName' ($Visibility) и загружаю код..."
    gh repo create $RepoName --$Visibility --source=. --remote=origin --push
}

# --- 3. Секреты из .env -> GitHub Secrets --------------------------------
$allowed = @("TRAVELPAYOUTS_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
$set = 0
foreach ($line in Get-Content ".env") {
    if ($line -match '^\s*([A-Z_]+)\s*=\s*(.+?)\s*$') {
        $name = $Matches[1]
        $value = $Matches[2]
        if ($allowed -contains $name -and $value) {
            gh secret set $name --body $value 1>$null
            Write-Host "  секрет установлен: $name" -ForegroundColor Green
            $set++
        }
    }
}
if ($set -lt 3) {
    Write-Host "Внимание: установлено секретов: $set из 3. Проверьте .env." -ForegroundColor Yellow
}

# --- Готово --------------------------------------------------------------
Write-Host ""
Write-Host "Готово! Репозиторий создан, ключи в секретах, расписание — каждые 30 минут." -ForegroundColor Cyan
Write-Host "Открыть Actions в браузере:  gh browse --repo $RepoName /actions" -ForegroundColor DarkGray
Write-Host "Запустить прогон прямо сейчас (не дожидаясь расписания):"
Write-Host "  gh workflow run 'ticket price monitor'" -ForegroundColor DarkGray
