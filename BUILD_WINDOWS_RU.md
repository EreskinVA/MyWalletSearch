# Инструкция по сборке VanitySearch на Windows

## Текущая конфигурация

- **Видеокарта**: NVIDIA GeForce GTX 1050 Ti
- **Compute Capability**: 6.1
- **CUDA**: v13.1 (установлена)
- **Путь CUDA**: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1`

## Варианты сборки

### Вариант 1: MSYS2 (рекомендуется)

1. **Установите MSYS2**:
   - Скачайте с https://www.msys2.org/
   - Установите в `C:\msys64`

2. **Установите компилятор**:
   ```bash
   # Откройте MSYS2 MinGW 64-bit terminal
   pacman -Syu
   pacman -S mingw-w64-x86_64-gcc
   ```

3. **Соберите проект**:
   ```powershell
   # В PowerShell из каталога проекта
   .\build_windows_gpu.ps1
   ```

### Вариант 2: Visual Studio

Если у вас установлена Visual Studio:

1. **Откройте Developer Command Prompt for VS**

2. **Перейдите в каталог проекта**:
   ```cmd
   cd C:\Users\User\Desktop\vanity\projectCode\MyWalletSearch
   ```

3. **Соберите проект**:
   ```cmd
   msbuild VanitySearch.vcxproj /p:Configuration=Release /p:Platform=x64
   ```

   Или откройте `VanitySearch.sln` в Visual Studio и соберите проект.

### Вариант 3: MinGW (альтернатива)

1. **Скачайте MinGW-w64**:
   - https://sourceforge.net/projects/mingw-w64/
   - Или используйте установщик WinLibs

2. **Добавьте в PATH**:
   - Путь к `bin` директории MinGW (например, `C:\MinGW\bin`)

3. **Соберите проект**:
   ```powershell
   .\build_windows_gpu.ps1
   ```

## Проверка grid для GTX 1050 Ti

После сборки проверьте допустимый grid:

```powershell
.\VanitySearch.exe -g 32,64 -check
```

Если видите ошибку OOM (out of memory), уменьшите grid:
- `-g 32,64` → `-g 16,64` → `-g 8,64`

## Тестовый запуск GPU поиска

После успешной сборки и проверки:

```powershell
# Простой тест (быстро найдет результат)
.\VanitySearch.exe -gpu -gpuId 0 -g 32,64 -t 2 -m 2000000 -o test_out.txt "1P*X"

# Или с префиксом
.\VanitySearch.exe -gpu -gpuId 0 -g 32,64 -t 2 -m 2000000 -o test_out.txt "18ss"
```

## Рекомендуемые параметры для GTX 1050 Ti

- **Grid**: `-g 32,64` или `-g 16,64` (зависит от доступной памяти)
- **Потоки CPU**: `-t 2` (можно увеличить до 4-8)
- **MaxFound**: `-m 2000000` (буфер результатов)
- **GPU ID**: `-gpuId 0` (если одна видеокарта)

## Устранение проблем

### Ошибка: "CUDA not found"
- Проверьте путь: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1`
- Установите CUDA Toolkit 13.1

### Ошибка: "Compiler not found"
- Установите MSYS2 или MinGW
- Или используйте Visual Studio

### Ошибка: "Kernel out of memory"
- Уменьшите grid: `-g 32,64` → `-g 16,64`
- Закройте другие приложения, использующие GPU

### Ошибка: "items lost"
- Увеличьте `-m`: `-m 2000000` → `-m 5000000`
- Или уменьшите grid

