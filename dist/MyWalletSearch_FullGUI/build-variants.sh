#!/bin/bash
#
# Сборка нескольких вариантов VanitySearch для сравнения
#

set -e

echo "=========================================="
echo "Сборка всех вариантов VanitySearch"
echo "=========================================="
echo ""

# Очистка
make clean 2>/dev/null || true
rm -f VanitySearch-* 2>/dev/null || true

# Вариант 1: Базовый (без оптимизаций)
echo "📦 Вариант 1: Базовый (без спец. оптимизаций)"
make CXXFLAGS="-O2 -I." all
mv VanitySearch VanitySearch-basic
echo "✅ VanitySearch-basic готов"
echo ""

make clean

# Вариант 2: SSE оптимизированный
echo "📦 Вариант 2: SSE оптимизированный"
make CXXFLAGS="-msse4.2 -O3 -I." all
mv VanitySearch VanitySearch-sse
echo "✅ VanitySearch-sse готов"
echo ""

make clean

# Вариант 3: AVX2 оптимизированный
echo "📦 Вариант 3: AVX2 оптимизированный"
make CXXFLAGS="-mavx2 -O3 -march=native -I." all 2>/dev/null && {
    mv VanitySearch VanitySearch-avx2
    echo "✅ VanitySearch-avx2 готов"
} || {
    echo "⚠️  AVX2 не поддерживается на этом CPU"
}
echo ""

make clean

# Вариант 4: AVX-512 оптимизированный
echo "📦 Вариант 4: AVX-512 оптимизированный"
if grep -q avx512f /proc/cpuinfo 2>/dev/null || sysctl -a 2>/dev/null | grep -q AVX512; then
    make -f Makefile.avx512 all 2>/dev/null && {
        mv VanitySearch VanitySearch-avx512
        echo "✅ VanitySearch-avx512 готов"
    } || {
        echo "⚠️  Ошибка компиляции AVX-512"
    }
else
    echo "⚠️  AVX-512 не поддерживается на этом CPU"
fi
echo ""

# Итоги
echo "=========================================="
echo "Результаты сборки:"
echo "=========================================="
ls -lh VanitySearch-* 2>/dev/null || echo "Нет собранных вариантов"
echo ""

echo "🎯 Для тестирования производительности:"
echo ""
echo "# Создать тестовый сегмент"
echo "echo '50.0 50.001 up test' > bench.txt"
echo ""
echo "# Тест каждого варианта"
echo "time ./VanitySearch-basic -seg bench.txt -bits 50 -t 4 1Test"
echo "time ./VanitySearch-sse -seg bench.txt -bits 50 -t 4 1Test"
echo "time ./VanitySearch-avx2 -seg bench.txt -bits 50 -t 4 1Test"
echo "time ./VanitySearch-avx512 -seg bench.txt -bits 50 -t 4 1Test"
echo ""
echo "Сравните время выполнения!"
echo ""

