# 🍎 Компиляция VanitySearch на macOS

## 📋 Предварительные требования

### 1. Установка Xcode Command Line Tools

```bash
xcode-select --install
```

### 2. Установка Homebrew (если еще не установлен)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 3. Установка необходимых компонентов

```bash
# GCC компилятор
brew install gcc

# Для проверки версии
gcc --version
g++ --version
```

## 🔨 Компиляция (только CPU)

**Важно**: macOS не поддерживает NVIDIA CUDA с 2017 года, поэтому компилируем только CPU версию.

### Метод 1: Стандартная компиляция

```bash
cd /Users/vladimirereskin/Projects/iiModel/VanitySearch
make clean
make all
```

### Метод 2: С явным указанием компилятора

Если возникают проблемы, попробуйте указать GCC явно:

```bash
make clean
make CXX=g++-13 all
```

(Замените `g++-13` на вашу версию GCC из `brew list gcc`)

### Метод 3: С оптимизацией для вашего процессора

```bash
make clean

# Для Intel Mac
make CXXFLAGS="-m64 -mssse3 -march=native -O3 -I." all

# Для Apple Silicon (M1/M2/M3)
make CXXFLAGS="-march=native -O3 -I." all
```

## 🧪 Проверка после компиляции

```bash
# Проверить, что файл создан
ls -lh VanitySearch

# Проверить архитектуру
file VanitySearch

# Запустить версию
./VanitySearch -v

# Быстрый тест
./VanitySearch -t 2 1Test
```

## ⚡ Возможные проблемы и решения

### Проблема 1: "xcrun: error: invalid active developer path"

**Решение**: Установите Xcode Command Line Tools
```bash
xcode-select --install
```

### Проблема 2: "g++: command not found"

**Решение**: Установите GCC через Homebrew
```bash
brew install gcc
```

### Проблема 3: Ошибки компиляции с `-mssse3`

**Для Apple Silicon (M1/M2/M3)**: 
```bash
# Отредактируйте Makefile, найдите строку с -mssse3 и замените на:
CXXFLAGS = -m64 -march=native -Wno-write-strings -O2 -I.
```

Или используйте:
```bash
make CXXFLAGS="-march=native -O3 -Wno-write-strings -I." LFLAGS="-lpthread" all
```

### Проблема 4: "fatal error: 'pthread.h' file not found"

**Решение**: Убедитесь, что Xcode Command Line Tools установлены
```bash
xcode-select -p
# Должно вывести: /Library/Developer/CommandLineTools

# Если нет, установите:
sudo xcode-select --reset
xcode-select --install
```

### Проблема 5: Предупреждения о deprecated функциях

Это нормально для macOS. Программа все равно будет работать. Чтобы подавить предупреждения:

```bash
make CXXFLAGS="-m64 -mssse3 -Wno-write-strings -Wno-deprecated -O2 -I." all
```

## 🎯 Оптимизация для вашей системы

### Определение типа процессора

```bash
sysctl -a | grep machdep.cpu.brand_string
```

### Intel Mac оптимизация

```bash
# Для старых Intel (до 2015)
make CXXFLAGS="-m64 -march=core2 -O3 -Wno-write-strings -I." all

# Для Intel (2015-2020)
make CXXFLAGS="-m64 -march=skylake -O3 -Wno-write-strings -I." all

# Для новых Intel (2020+)
make CXXFLAGS="-m64 -march=native -O3 -Wno-write-strings -I." all
```

### Apple Silicon оптимизация (M1/M2/M3)

```bash
# Базовая оптимизация
make CXXFLAGS="-mcpu=apple-m1 -O3 -Wno-write-strings -I." all

# Агрессивная оптимизация
make CXXFLAGS="-mcpu=apple-m1 -O3 -flto -Wno-write-strings -I." all
```

## 📊 Ожидаемая производительность на macOS

### Intel Mac
- **MacBook Pro 16" 2019** (i9-9980HK): ~8-12 MKey/s
- **Mac Pro 2019** (Xeon W): ~15-20 MKey/s
- **iMac 27" 2020** (i9-10910): ~10-15 MKey/s

### Apple Silicon Mac
- **MacBook Air M1**: ~12-18 MKey/s
- **MacBook Pro M1 Pro**: ~20-30 MKey/s
- **Mac Studio M1 Ultra**: ~40-60 MKey/s
- **MacBook Pro M3 Max**: ~35-50 MKey/s

*Производительность зависит от количества потоков и термального throttling*

## 🚀 Запуск после компиляции

### Базовый тест

```bash
# Простой поиск префикса
./VanitySearch -t 4 1Test

# Сегментированный поиск для Puzzle 71
./VanitySearch -seg segments_puzzle71.txt -bits 71 -t 8 1FshYo

# Оптимальное количество потоков (все физические ядра)
# Для M1 (8 ядер): -t 8
# Для M1 Pro (10 ядер): -t 10
# Для M1 Max (10 ядер): -t 10
# Для M2 Ultra (24 ядра): -t 24

# Пример для M1 Pro
./VanitySearch -seg segments_puzzle71.txt -bits 71 -t 10 -o results.txt 1FshYo
```

### Оптимальные настройки потоков

```bash
# Узнать количество ядер
sysctl -n hw.ncpu          # Логические ядра
sysctl -n hw.physicalcpu   # Физические ядра

# Используйте количество физических ядер для максимальной производительности
./VanitySearch -seg segments_puzzle71.txt -bits 71 -t $(sysctl -n hw.physicalcpu) 1FshYo
```

## 🔥 Управление температурой

На Mac, особенно на ноутбуках, следите за температурой:

### Мониторинг

```bash
# Установите мониторинг (опционально)
brew install stats

# Или используйте встроенный Activity Monitor
open -a "Activity Monitor"
```

### Снижение нагрузки при перегреве

```bash
# Уменьшите количество потоков
./VanitySearch -seg segments_puzzle71.txt -bits 71 -t 4 1FshYo

# Для ноутбуков рекомендуется использовать 50-75% ядер
# Например, для M1 (8 ядер) используйте -t 4 или -t 6
```

## 🐛 Отладка при проблемах

### Компиляция с отладочной информацией

```bash
make clean
make debug=1 all

# Запуск с отладкой
./VanitySearch -seg segments_puzzle71.txt -bits 71 -t 2 1FshYo
```

### Проверка зависимостей

```bash
# Проверить линковку
otool -L VanitySearch

# Должно показать что-то вроде:
# /usr/lib/libSystem.B.dylib
# /usr/lib/libc++.1.dylib
```

### Verbose вывод при компиляции

```bash
make clean
make V=1 all
```

## 📝 Создание универсального бинарника (Intel + Apple Silicon)

Если нужен бинарник для обеих архитектур:

```bash
# Компиляция для Intel
make clean
arch -x86_64 make CXX="g++ -arch x86_64" all
mv VanitySearch VanitySearch-intel

# Компиляция для ARM (Apple Silicon)
make clean
arch -arm64 make CXX="g++ -arch arm64" all
mv VanitySearch VanitySearch-arm

# Создание универсального бинарника
lipo -create VanitySearch-intel VanitySearch-arm -output VanitySearch-universal

# Проверка
file VanitySearch-universal
# Должно показать: Mach-O universal binary with 2 architectures
```

## ⚙️ Автоматизация (опционально)

Создайте скрипт `build-macos.sh`:

```bash
#!/bin/bash

echo "🔨 Компиляция VanitySearch для macOS..."

# Очистка
make clean

# Определение архитектуры
ARCH=$(uname -m)

if [[ "$ARCH" == "arm64" ]]; then
    echo "🍎 Обнаружен Apple Silicon (M-серия)"
    make CXXFLAGS="-mcpu=apple-m1 -O3 -Wno-write-strings -I." all
elif [[ "$ARCH" == "x86_64" ]]; then
    echo "🔧 Обнаружен Intel процессор"
    make CXXFLAGS="-m64 -march=native -O3 -Wno-write-strings -I." all
fi

if [ -f "VanitySearch" ]; then
    echo "✅ Компиляция успешна!"
    echo "📊 Размер файла: $(ls -lh VanitySearch | awk '{print $5}')"
    echo "🏗️  Архитектура: $(file VanitySearch)"
    echo ""
    echo "🚀 Для запуска:"
    echo "   ./VanitySearch -seg segments_puzzle71.txt -bits 71 -t 8 1FshYo"
else
    echo "❌ Ошибка компиляции"
    exit 1
fi
```

Сделайте его исполняемым:
```bash
chmod +x build-macos.sh
./build-macos.sh
```

## 🎯 Финальная проверка

После успешной компиляции:

```bash
# 1. Проверка версии
./VanitySearch -v

# 2. Тест стандартного режима
timeout 5s ./VanitySearch -t 2 1Test

# 3. Тест сегментированного режима
./test_segment_search.sh

# 4. Запуск на Puzzle 71
./VanitySearch -seg segments_puzzle71.txt -bits 71 -t $(sysctl -n hw.physicalcpu) 1FshYo
```

## 💡 Советы для macOS

1. **Используйте Terminal или iTerm2** для лучшего опыта
2. **Закройте другие приложения** для максимальной производительности
3. **Подключите к питанию** ноутбуки для предотвращения throttling
4. **Используйте охлаждающую подставку** для ноутбуков
5. **Мониторьте температуру** через Activity Monitor или Stats
6. **Не используйте все ядра** на ноутбуках (оставьте 25% свободными)

## 🔗 Полезные ссылки

- Оригинальный VanitySearch: https://github.com/JeanLucPons/VanitySearch
- Homebrew: https://brew.sh
- GCC на macOS: https://formulae.brew.sh/formula/gcc

## 📄 Лицензия

GPL v3 (как оригинальный VanitySearch)

---

**Удачной компиляции! 🍀🔧**

