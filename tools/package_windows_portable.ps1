param(
  # Папка, куда собрать portable-набор
  [string]$OutDir = (Join-Path $PSScriptRoot "..\dist\VanitySearch_portable"),
  # Если true — включить sqlite3.dll (нужно для режима -db)
  [bool]$WithSqlite = $true
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$p) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

# Найти самый свежий VanitySearch.exe (обычно x64\ReleaseSM61 или x64\Release)
$exe = Get-ChildItem -Path $repoRoot -Recurse -Filter "VanitySearch.exe" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if (-not $exe) { throw "Не найден VanitySearch.exe. Сначала соберите проект." }

Ensure-Dir $OutDir

Copy-Item -Force $exe.FullName (Join-Path $OutDir "VanitySearch.exe")

if ($WithSqlite) {
  $sqliteDll = Join-Path $repoRoot "third_party\sqlite\bin\sqlite3.dll"
  if (-not (Test-Path $sqliteDll)) {
    Write-Host "sqlite3.dll не найден в third_party\sqlite\bin. Скачиваю..."
    & (Join-Path $PSScriptRoot "fetch_sqlite_windows.ps1") | Out-Host
  }
  if (Test-Path $sqliteDll) {
    Copy-Item -Force $sqliteDll (Join-Path $OutDir "sqlite3.dll")
  } else {
    throw "sqlite3.dll всё ещё не найден после скачивания."
  }
}

# Мини-README для запуска на другом ПК
$readme = @"
VanitySearch portable (Windows)

Файлы:
- VanitySearch.exe
$(if ($WithSqlite) { "- sqlite3.dll (нужно только если используете -db)" } else { "" })

Запуск примеров:
  VanitySearch.exe -v
  VanitySearch.exe -h

Если используете базу:
  VanitySearch.exe -db bitcoin_addresses_optimized.sqlite -t 4

Примечание:
- Сборка сделана с /MT, поэтому Visual C++ Redistributable обычно не нужен.
"@

Set-Content -Encoding UTF8 -Path (Join-Path $OutDir "README_PORTABLE_RU.txt") -Value $readme

Write-Host "OK: portable folder -> $OutDir"


