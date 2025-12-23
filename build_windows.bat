@echo off
REM ============================================
REM WINDOWS BUILD SCRIPT для VanitySearch
REM Компиляция через MSBuild (без Visual Studio IDE)
REM ============================================

echo.
echo ============================================
echo   КОМПИЛЯЦИЯ VANITYSEARCH ДЛЯ WINDOWS
echo ============================================
echo.

REM Проверка наличия MSBuild
set "MSBUILD_PATH="
if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" (
    set "MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" (
    set "MSBUILD_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"
) else if exist "C:\Program Files\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe" (
    set "MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe"
) else (
    echo [ОШИБКА] MSBuild не найден!
    echo.
    echo Установите Visual Studio с компонентом "Desktop development with C++"
    echo Или используйте Developer Command Prompt для VS
    echo.
    pause
    exit /b 1
)

echo [OK] MSBuild найден: %MSBUILD_PATH%
echo.

REM Очистка предыдущей сборки
echo [1/3] Очистка предыдущей сборки...
"%MSBUILD_PATH%" VanitySearch.sln /t:Clean /p:Configuration=Release /p:Platform=x64 /nologo /v:minimal
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Очистка завершилась с ошибками (это нормально, если проект не компилировался ранее)
)
echo.

REM Компиляция
echo [2/3] Компиляция проекта (Release, x64)...
"%MSBUILD_PATH%" VanitySearch.sln /t:Rebuild /p:Configuration=Release /p:Platform=x64 /nologo /v:minimal
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Компиляция не удалась!
    echo.
    echo Возможные причины:
    echo 1. Не установлен "Desktop development with C++" в Visual Studio
    echo 2. Не установлен CUDA Toolkit (если используете GPU)
    echo 3. Неправильная версия Visual Studio
    echo.
    pause
    exit /b 1
)
echo.

REM Проверка результата
echo [3/3] Проверка результата...
if exist "x64\Release\VanitySearch.exe" (
    echo.
    echo ============================================
    echo   КОМПИЛЯЦИЯ УСПЕШНА! ✅
    echo ============================================
    echo.
    echo Исполняемый файл: x64\Release\VanitySearch.exe
    echo.
    echo Для проверки GPU запустите:
    echo   x64\Release\VanitySearch.exe -l
    echo.
) else (
    echo.
    echo [ОШИБКА] Исполняемый файл не найден!
    echo Ожидался: x64\Release\VanitySearch.exe
    echo.
    pause
    exit /b 1
)

pause

