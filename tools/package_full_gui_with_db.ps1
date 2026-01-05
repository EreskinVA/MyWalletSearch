param(
  # Путь к базе SQLite, которую нужно включить в пакет
  [Parameter(Mandatory = $true)]
  [string]$DatabasePath,

  # Папка, куда собрать полный пакет
  # (оставьте пустым, чтобы использовать dist\MyWalletSearch_FullGUI)
  [string]$OutDir = "",

  # Конфигурация, откуда брать exe (ReleaseSM61 по умолчанию)
  [ValidateSet("ReleaseSM61","Release")]
  [string]$Config = "ReleaseSM61"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$p) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $repoRoot "dist\\MyWalletSearch_FullGUI"
}
$db = Resolve-Path $DatabasePath

if (-not (Test-Path $db)) { throw "База не найдена: $DatabasePath" }

$exe = Join-Path $repoRoot ("x64\\$Config\\VanitySearch.exe")
if (-not (Test-Path $exe)) {
  throw "Не найден exe: $exe. Укажите правильный -Config или соберите проект."
}

$sqliteDll = Join-Path $repoRoot "third_party\\sqlite\\bin\\sqlite3.dll"
if (-not (Test-Path $sqliteDll)) {
  Write-Host "sqlite3.dll не найден. Скачиваю..."
  & (Join-Path $scriptDir "fetch_sqlite_windows.ps1") | Out-Host
}
if (-not (Test-Path $sqliteDll)) { throw "sqlite3.dll не найден (third_party\\sqlite\\bin\\sqlite3.dll)" }

# Пересоздать OutDir
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
Ensure-Dir $OutDir

# 1) Копируем исходники/скрипты (почти весь репозиторий), без мусора
$excludeDirs = @(
  ".git",
  "dist",
  "obj",
  "__pycache__",
  "runs",
  "runs_cpu_gui",
  "server_results",
  "x64"
)

Write-Host "Copying repo files (excluding build/output dirs)..."

foreach ($item in Get-ChildItem -LiteralPath $repoRoot -Force) {
  if ($excludeDirs -contains $item.Name) { continue }
  $dst = Join-Path $OutDir $item.Name
  Copy-Item -Recurse -Force -LiteralPath $item.FullName -Destination $dst
}

# 2) Бинарник + sqlite dll в ожидаемое GUI место
$binDir = Join-Path $OutDir ("x64\\$Config")
Ensure-Dir $binDir
Copy-Item -Force $exe (Join-Path $binDir "VanitySearch.exe")
Copy-Item -Force $sqliteDll (Join-Path $binDir "sqlite3.dll")

# 3) База в db/
$dbDir = Join-Path $OutDir "db"
Ensure-Dir $dbDir
Copy-Item -Force $db (Join-Path $dbDir (Split-Path -Leaf $db))

# 4) BAT для запуска GUI
$bat = @"
@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python не найден.
  echo Установите Python 3.x (включая tkinter) и повторите запуск.
  echo Подсказка: поставьте галочку "Add Python to PATH".
  pause
  exit /b 1
)

set PYTHONUTF8=1
python vanity_gui.py
"@
Set-Content -Encoding ASCII -Path (Join-Path $OutDir "start_gui.bat") -Value $bat

# 5) README
$readme = @"
MyWalletSearch Full GUI package (Windows)

Что внутри:
- vanity_gui_unified.py / vanity_gui.py (GUI)
- x64\\$Config\\VanitySearch.exe (ваш бинарник)
- x64\\$Config\\sqlite3.dll (SQLite runtime для режима -db)
- db\\$(Split-Path -Leaf $db) (ваша база)

Запуск:
- Двойной клик по start_gui.bat

Важно:
- Нужен установленный Python 3.x с tkinter.
- База выбирается в GUI через "Browse DB..." (лежит в папке db).
"@
Set-Content -Encoding UTF8 -Path (Join-Path $OutDir "README_FULLGUI_RU.txt") -Value $readme

Write-Host "OK: Full GUI package -> $OutDir"


