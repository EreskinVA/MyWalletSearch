# Быстрая установка и сборка на Windows

## Шаг 1: Установка компилятора (выберите один вариант)

### Вариант A: MSYS2 (самый простой, ~5 минут)

1. Скачайте MSYS2: https://www.msys2.org/
2. Установите в `C:\msys64` (по умолчанию)
3. Откройте **MSYS2 MinGW 64-bit** (не MSYS2!)
4. Выполните:
   ```bash
   pacman -Syu
   pacman -S mingw-w64-x86_64-gcc
   ```
5. Закройте терминал MSYS2

### Вариант B: Chocolatey (если установлен)

```powershell
choco install mingw -y
```

### Вариант C: Visual Studio Build Tools

1. Скачайте: https://visualstudio.microsoft.com/downloads/
2. Выберите "Build Tools for Visual Studio"
3. Установите "Desktop development with C++"

## Шаг 2: Сборка проекта

После установки компилятора:

```powershell
# В PowerShell из каталога проекта
.\build_windows_gpu.ps1
```

## Шаг 3: Проверка

```powershell
.\VanitySearch.exe -g 32,64 -check
```

## Шаг 4: Тестовый запуск

```powershell
.\VanitySearch.exe -gpu -gpuId 0 -g 32,64 -t 2 -m 2000000 -o test.txt "1P*X"
```

## Если что-то не работает

1. **Компилятор не найден**: Убедитесь, что MSYS2 установлен в `C:\msys64` или добавьте MinGW в PATH
2. **CUDA не найдена**: Проверьте путь `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1`
3. **OOM ошибка**: Уменьшите grid до `-g 16,64` или `-g 8,64`

