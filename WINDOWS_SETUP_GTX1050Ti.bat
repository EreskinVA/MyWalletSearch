@echo off
REM Автоматическая установка и запуск на Windows
REM Для GTX 1050 Ti

echo ========================================
echo MyWalletSearch - Setup для Windows
echo ========================================
echo.

REM Проверка Git
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git не установлен!
    echo Скачайте: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Клонирование репозитория
echo Клонирование репозитория...
cd %USERPROFILE%\Documents
if exist MyWalletSearch (
    echo Директория уже существует, обновляем...
    cd MyWalletSearch
    git pull
) else (
    git clone https://github.com/EreskinVA/MyWalletSearch.git
    cd MyWalletSearch
)

echo.
echo ✅ Репозиторий готов
echo.

REM Проверка Visual Studio
echo Проверка Visual Studio...
if exist "VanitySearch.sln" (
    echo ✅ Файл проекта найден
    echo.
    echo СЛЕДУЮЩИЕ ШАГИ:
    echo 1. Откройте VanitySearch.sln в Visual Studio
    echo 2. Выберите Configuration: Release (не Debug!)
    echo 3. Выберите Platform: x64
    echo 4. Build - Rebuild Solution
    echo 5. После компиляции запустите:
    echo    x64\Release\VanitySearch.exe -l
    echo 6. Затем запустите поиск (команды ниже)
    echo.
) else (
    echo ERROR: VanitySearch.sln не найден!
)

echo ========================================
echo КОМАНДЫ ДЛЯ ЗАПУСКА (после компиляции):
echo ========================================
echo.
echo # Проверка GPU:
echo x64\Release\VanitySearch.exe -l
echo.
echo # Запуск поиска (зона 54-62%%):
echo x64\Release\VanitySearch.exe -seg segments_54-62_GTX1050Ti.txt -bits 71 -kangaroo -progress puzzle71.dat -gpu -gpuId 0 -g 256,128 -t 4 -o SOLUTION.txt 1PWo3JeB
echo.

pause

