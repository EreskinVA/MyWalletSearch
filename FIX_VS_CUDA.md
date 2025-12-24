# Исправление ошибки CUDA в Visual Studio

## Проблема

Ошибка: `импортированный проект "CUDA 11.1.props" не найден`

## Решение

Я обновил файл `VanitySearch.vcxproj` для использования CUDA 13.1 (ваша версия) вместо CUDA 11.1.

### Что было сделано:

1. ✅ Обновлены ссылки с CUDA 11.1 на CUDA 13.1
2. ✅ Добавлены альтернативные пути к CUDA integration files
3. ✅ Настроен Compute Capability 6.1 для GTX 1050 Ti

### Если ошибка все еще возникает:

#### Вариант 1: Копировать файлы CUDA в Visual Studio (рекомендуется)

1. Найдите вашу установку Visual Studio (обычно):
   - `C:\Program Files\Microsoft Visual Studio\2022\Community\`
   - или `C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\`

2. Найдите папку BuildCustomizations:
   - `[VS Path]\MSBuild\Microsoft\VC\v[version]\BuildCustomizations\`
   - Например: `v170`, `v180`, `v190`

3. Скопируйте файлы из:
   ```
   C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\extras\visual_studio_integration\MSBuildExtensions\
   ```
   
   В папку BuildCustomizations:
   - `CUDA 13.1.props`
   - `CUDA 13.1.targets`
   - `CUDA 13.1.xml` (если есть)

4. Перезапустите Visual Studio

#### Вариант 2: Использовать альтернативную сборку

Если не хотите копировать файлы, используйте PowerShell скрипт:

```powershell
.\build_windows_gpu.ps1
```

Этот скрипт собирает проект без Visual Studio integration files.

#### Вариант 3: Установить CUDA Toolkit с интеграцией Visual Studio

1. Переустановите CUDA Toolkit 13.1
2. При установке выберите "Visual Studio Integration"
3. Это автоматически скопирует файлы в Visual Studio

## Проверка после исправления

После исправления попробуйте собрать проект в Visual Studio:

1. Откройте `VanitySearch.sln` или `VanitySearch.vcxproj`
2. Выберите конфигурацию: **Release** или **ReleaseSM30**
3. Платформа: **x64**
4. Build -> Build Solution (Ctrl+Shift+B)

## Настройки для GTX 1050 Ti

Проект настроен для:
- **Compute Capability**: 6.1 (GTX 1050 Ti)
- **CUDA Version**: 13.1
- **Configuration**: Release (оптимизированная сборка)

## Если все еще не работает

Используйте альтернативный метод сборки:

```powershell
# Установите компилятор (если еще не установлен)
# См. QUICK_FIX_MSYS2.md

# Соберите проект
.\build_windows_gpu.ps1

# Проверьте
.\VanitySearch.exe -g 32,64 -check
```


