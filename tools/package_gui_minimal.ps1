param(
  [string]$OutDir = "",
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
  $OutDir = Join-Path $repoRoot "dist\\MyWalletSearch_GUI_MIN"
}

$exe = Join-Path $repoRoot ("x64\\$Config\\VanitySearch.exe")
if (-not (Test-Path $exe)) { throw "VanitySearch.exe not found: $exe (build it or change -Config)" }

$sqliteDll = Join-Path $repoRoot "third_party\\sqlite\\bin\\sqlite3.dll"
if (-not (Test-Path $sqliteDll)) {
  Write-Host "sqlite3.dll not found. Downloading..."
  & (Join-Path $scriptDir "fetch_sqlite_windows.ps1") | Out-Host
}
if (-not (Test-Path $sqliteDll)) { throw "sqlite3.dll not found: $sqliteDll" }

# Пересоздать OutDir
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
Ensure-Dir $OutDir

# Минимальный набор python-файлов для GUI + анализа/прогресса/генератора сегментов
$pyFiles = @(
  "vanity_gui_unified.py",
  "vanity_gui.py",
  "show_segment_progress.py",
  "analyze_seg_74_5_76.py",
  "smart_segment_generator.py"
)

foreach ($f in $pyFiles) {
  $src = Join-Path $repoRoot $f
  if (-not (Test-Path $src)) { throw "Required python file not found: $f" }
  Copy-Item -Force $src (Join-Path $OutDir $f)
}

# Папка для бинарника (GUI сам умеет находить x64\ReleaseSM61\VanitySearch.exe)
$binDir = Join-Path $OutDir ("x64\\$Config")
Ensure-Dir $binDir
Copy-Item -Force $exe (Join-Path $binDir "VanitySearch.exe")
Copy-Item -Force $sqliteDll (Join-Path $binDir "sqlite3.dll")

# Папка под базу (пустая, вы скопируете сами)
Ensure-Dir (Join-Path $OutDir "db")

# BAT для запуска
$batLines = @(
  "@echo off",
  "setlocal",
  "cd /d %~dp0",
  "",
  "where python >nul 2>nul",
  "if errorlevel 1 (",
  "  echo [ERROR] Python not found. Install Python 3.x with tkinter and try again.",
  "  pause",
  "  exit /b 1",
  ")",
  "",
  "set PYTHONUTF8=1",
  "python vanity_gui.py"
)
Set-Content -Encoding ASCII -Path (Join-Path $OutDir "start_gui.bat") -Value ($batLines -join "`r`n")

Write-Host "OK: GUI MIN package -> $OutDir"


