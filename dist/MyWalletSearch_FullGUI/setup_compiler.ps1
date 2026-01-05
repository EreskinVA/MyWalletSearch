# Script to check for C++ compilers on Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Checking for C++ compilers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$compilerFound = $false

# Check MSYS2
if (Test-Path "C:\msys64\mingw64\bin\g++.exe") {
    Write-Host "OK: MSYS2 MinGW found!" -ForegroundColor Green
    Write-Host "   Path: C:\msys64\mingw64\bin\g++.exe" -ForegroundColor White
    $compilerFound = $true
}

# Check MinGW
if (-not $compilerFound -and (Test-Path "C:\MinGW\bin\g++.exe")) {
    Write-Host "OK: MinGW found!" -ForegroundColor Green
    Write-Host "   Path: C:\MinGW\bin\g++.exe" -ForegroundColor White
    $compilerFound = $true
}

# Check Visual Studio
if (-not $compilerFound) {
    $vsPath = Get-ChildItem "C:\Program Files\Microsoft Visual Studio" -ErrorAction SilentlyContinue | 
              Where-Object { $_.Name -match "20\d\d" } | 
              Sort-Object Name -Descending | 
              Select-Object -First 1
    
    if ($vsPath) {
        Write-Host "OK: Visual Studio found!" -ForegroundColor Green
        Write-Host "   Version: $($vsPath.Name)" -ForegroundColor White
        Write-Host ""
        Write-Host "To build, use:" -ForegroundColor Yellow
        Write-Host "   msbuild VanitySearch.vcxproj /p:Configuration=Release /p:Platform=x64" -ForegroundColor White
        $compilerFound = $true
    }
}

if (-not $compilerFound) {
    Write-Host "WARNING: C++ compiler not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installation options:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. MSYS2 (recommended, ~200 MB):" -ForegroundColor Cyan
    Write-Host "   - Download: https://www.msys2.org/" -ForegroundColor White
    Write-Host "   - Install to C:\msys64" -ForegroundColor White
    Write-Host "   - Open MSYS2 MinGW 64-bit" -ForegroundColor White
    Write-Host "   - Run: pacman -Syu" -ForegroundColor White
    Write-Host "   - Run: pacman -S mingw-w64-x86_64-gcc" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Chocolatey (if installed):" -ForegroundColor Cyan
    Write-Host "   choco install mingw -y" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Visual Studio Build Tools:" -ForegroundColor Cyan
    Write-Host "   - https://visualstudio.microsoft.com/downloads/" -ForegroundColor White
    Write-Host "   - Select 'Build Tools for Visual Studio'" -ForegroundColor White
    Write-Host "   - Install 'Desktop development with C++'" -ForegroundColor White
    Write-Host ""
    Write-Host "After installation, run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Compiler ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Now you can build the project:" -ForegroundColor Yellow
Write-Host "   .\build_windows_gpu.ps1" -ForegroundColor White
Write-Host ""
