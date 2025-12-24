# Script to fix MSYS2 mirror issues
# Configures faster mirrors for MSYS2

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing MSYS2 mirror configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$msys2Path = "C:\msys64"
if (-not (Test-Path $msys2Path)) {
    Write-Host "ERROR: MSYS2 not found at $msys2Path" -ForegroundColor Red
    Write-Host "Install MSYS2 first from https://www.msys2.org/" -ForegroundColor Yellow
    exit 1
}

$pacmanConf = Join-Path $msys2Path "etc\pacman.d\mirrorlist.mingw64"
$pacmanConf32 = Join-Path $msys2Path "etc\pacman.d\mirrorlist.mingw32"
$pacmanConfMsys = Join-Path $msys2Path "etc\pacman.d\mirrorlist.msys"

Write-Host "Backing up existing mirror lists..." -ForegroundColor Yellow

# Backup existing configs
if (Test-Path $pacmanConf) {
    Copy-Item $pacmanConf "$pacmanConf.backup" -Force
}
if (Test-Path $pacmanConf32) {
    Copy-Item $pacmanConf32 "$pacmanConf32.backup" -Force
}
if (Test-Path $pacmanConfMsys) {
    Copy-Item $pacmanConfMsys "$pacmanConfMsys.backup" -Force
}

Write-Host "OK: Backups created" -ForegroundColor Green
Write-Host ""

# Fast mirrors (prioritize closer ones)
$fastMirrors = @"
## Fast mirrors for MSYS2
## Uncomment the mirror you want to use

## Germany (usually fast)
Server = https://mirror.fcix.net/msys2/mingw/x86_64
Server = https://mirror.selfnet.de/msys2/mingw/x86_64

## USA
Server = https://repo.msys2.org/mingw/x86_64

## Japan (if in Asia)
#Server = https://mirrors.cat.net/msys2/mingw/x86_64

## China (if in China)
#Server = https://mirrors.tuna.tsinghua.edu.cn/msys2/mingw/x86_64
"@

Write-Host "Updating mirror lists with faster mirrors..." -ForegroundColor Yellow

# Update mirror lists
Set-Content -Path $pacmanConf -Value $fastMirrors -Encoding UTF8
Set-Content -Path $pacmanConf32 -Value $fastMirrors -Encoding UTF8
Set-Content -Path $pacmanConfMsys -Value $fastMirrors -Encoding UTF8

Write-Host "OK: Mirror lists updated" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Mirror configuration updated!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Now try installing again in MSYS2 MinGW 64-bit:" -ForegroundColor Yellow
Write-Host "  pacman -Syu" -ForegroundColor White
Write-Host "  pacman -S mingw-w64-x86_64-gcc" -ForegroundColor White
Write-Host ""
Write-Host "If still slow, try:" -ForegroundColor Yellow
Write-Host "  pacman -Syu --noconfirm" -ForegroundColor White
Write-Host "  pacman -S mingw-w64-x86_64-gcc --noconfirm" -ForegroundColor White
Write-Host ""


