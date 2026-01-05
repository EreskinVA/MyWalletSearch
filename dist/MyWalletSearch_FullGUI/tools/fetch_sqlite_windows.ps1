param(
  # Куда положить sqlite3.dll (по умолчанию: в репозиторий)
  [string]$OutDir = (Join-Path $PSScriptRoot "..\third_party\sqlite\bin"),
  # Архитектура: x64 (по умолчанию) или x86
  [ValidateSet("x64","x86")]
  [string]$Arch = "x64"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$p) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

Ensure-Dir $OutDir

$downloadPage = "https://www.sqlite.org/download.html"
Write-Host "Fetching SQLite download page: $downloadPage"
$html = Invoke-WebRequest -UseBasicParsing $downloadPage

$pattern = if ($Arch -eq "x64") { 'sqlite-dll-win-x64-\d+\.zip' } else { 'sqlite-dll-win-x86-\d+\.zip' }
$m = [regex]::Match($html.Content, $pattern)
if (-not $m.Success) {
  throw "Не удалось найти ссылку на zip для $Arch на странице $downloadPage (pattern: $pattern)"
}

$zipName = $m.Value

# На download.html ссылка может вести на JS-страницу (hp?.html). Прямой файл обычно лежит в подпапке года:
#   https://www.sqlite.org/2026/sqlite-dll-win-x64-....zip
# Поэтому пробуем несколько лет назад, пока не найдём рабочий URL.
$yearNow = (Get-Date).Year
$zipUrl = $null
foreach ($y in ($yearNow..2010)) {
  $candidate = "https://www.sqlite.org/$y/$zipName"
  try {
    Invoke-WebRequest -UseBasicParsing -Method Head $candidate | Out-Null
    $zipUrl = $candidate
    break
  } catch {
    # ignore
  }
}
if (-not $zipUrl) {
  # fallback: иногда файл может лежать в корне (старые версии)
  $zipUrl = "https://www.sqlite.org/$zipName"
}

$tmp = Join-Path $env:TEMP ("sqlite_" + $Arch + "_" + [guid]::NewGuid().ToString("N"))
Ensure-Dir $tmp

$zipPath = Join-Path $tmp $zipName
Write-Host "Downloading: $zipUrl"
Invoke-WebRequest -UseBasicParsing $zipUrl -OutFile $zipPath

Write-Host "Extracting: $zipPath"
Expand-Archive -Force -Path $zipPath -DestinationPath $tmp

$dll = Get-ChildItem -Path $tmp -Recurse -Filter "sqlite3.dll" | Select-Object -First 1
if (-not $dll) {
  throw "В архиве не найден sqlite3.dll"
}

$dst = Join-Path $OutDir "sqlite3.dll"
Copy-Item -Force $dll.FullName $dst
Write-Host "OK: sqlite3.dll -> $dst"


