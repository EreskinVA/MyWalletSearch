# Script to help install WinLibs MinGW
# Alternative to MSYS2 if mirror issues persist

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "WinLibs MinGW Installation Helper" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "WinLibs provides pre-built MinGW-w64 GCC without package manager." -ForegroundColor Yellow
Write-Host "This is faster if MSYS2 mirrors are slow." -ForegroundColor Yellow
Write-Host ""

Write-Host "Steps:" -ForegroundColor Cyan
Write-Host "1. Download WinLibs from: https://winlibs.com/" -ForegroundColor White
Write-Host "2. Choose: GCC 13.x (or newer) + MinGW-w64 UCRT runtime" -ForegroundColor White
Write-Host "3. Extract to: C:\MinGW" -ForegroundColor White
Write-Host "4. Run this script again to verify" -ForegroundColor White
Write-Host ""

$mingwPath = "C:\MinGW\bin\g++.exe"
if (Test-Path $mingwPath) {
    Write-Host "OK: WinLibs/MinGW found at C:\MinGW" -ForegroundColor Green
    Write-Host ""
    Write-Host "Testing compiler..." -ForegroundColor Yellow
    & $mingwPath --version
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "OK: Compiler works!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Now you can build:" -ForegroundColor Yellow
        Write-Host "  .\build_windows_gpu.ps1" -ForegroundColor White
    }
} else {
    Write-Host "WinLibs not found at C:\MinGW\bin\g++.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Download link: https://winlibs.com/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "After downloading and extracting to C:\MinGW, run this script again." -ForegroundColor Yellow
}

Write-Host ""


