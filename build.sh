#!/bin/bash
#
# Автоматическая сборка VanitySearch с оптимальными настройками
# Определяет CPU и выбирает правильные флаги компиляции
#

set -e

echo "=========================================="
echo "VanitySearch - Автоматическая сборка"
echo "=========================================="
echo ""

# Определение ОС
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "Система: $OS $ARCH"
echo ""

# Проверка поддержки AVX-512
check_avx512() {
    if [ "$OS" = "Linux" ]; then
        if grep -q avx512f /proc/cpuinfo 2>/dev/null; then
            return 0
        fi
    elif [ "$OS" = "Darwin" ]; then
        if sysctl -a 2>/dev/null | grep -q AVX512; then
            return 0
        fi
    fi
    return 1
}

# Определение оптимальных флагов
CXXFLAGS_OPT=""
USE_AVX512=false

if check_avx512; then
    echo "✅ AVX-512 обнаружен!"
    echo "Компиляция с AVX-512 поддержкой..."
    USE_AVX512=true
    CXXFLAGS_OPT="-mavx512f -mavx512dq -mavx512bw -mavx512vl -O3 -march=native"
else
    echo "⚠️  AVX-512 не обнаружен"
    echo "Компиляция со стандартными оптимизациями..."
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        # Apple Silicon или ARM
        CXXFLAGS_OPT="-O3 -march=native"
    else
        # Intel/AMD без AVX-512
        CXXFLAGS_OPT="-mavx2 -O3 -march=native"
    fi
fi

echo ""
echo "Флаги компиляции: $CXXFLAGS_OPT"
echo ""

# Очистка
echo "🧹 Очистка старых файлов..."
make clean 2>/dev/null || true

# Компиляция
echo "🔨 Компиляция..."
echo ""

if [ "$USE_AVX512" = true ]; then
    # Компиляция с AVX-512
    if [ -f "Makefile.avx512" ]; then
        make -f Makefile.avx512 all
    else
        make CXXFLAGS="$CXXFLAGS_OPT -I." all
    fi
else
    # Стандартная компиляция
    make CXXFLAGS="$CXXFLAGS_OPT -I." all
fi

# Проверка результата
if [ -f "VanitySearch" ]; then
    echo ""
    echo "=========================================="
    echo "✅ Компиляция успешна!"
    echo "=========================================="
    echo ""
    
    # Информация о бинарнике
    ls -lh VanitySearch
    file VanitySearch
    
    echo ""
    echo "🎯 Для запуска:"
    echo "   ./VanitySearch -seg segments_puzzle71.txt -bits 71 -t 8 1FshYo"
    echo ""
    
    if [ "$USE_AVX512" = true ]; then
        echo "⚡ AVX-512 включен - ожидаемое ускорение: 4-8x"
        echo ""
    fi
    
    echo "📚 Документация:"
    echo "   cat QUICK_START_RU.md"
    if [ "$USE_AVX512" = true ]; then
        echo "   cat AVX512_GUIDE.md"
    fi
    echo ""
    
else
    echo ""
    echo "=========================================="
    echo "❌ Ошибка компиляции"
    echo "=========================================="
    echo ""
    echo "Попробуйте вручную:"
    echo "   make clean"
    echo "   make all"
    echo ""
    exit 1
fi

