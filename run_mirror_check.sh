#!/bin/bash
# Проверка зеркального диапазона (28-29% puzzle71)
# Согласно анализу п. 4.3: Half-point mirror

set -euo pipefail

# Параметры
SEG_FILE="seg_mirror.txt"
OUT_FILE="out_mirror.txt"
LOG_FILE="log_mirror.log"
PROGRESS_FILE="progress_mirror.dat"
PATTERN="1PWo3JeB9jr"  # Целевой паттерн
BITS=71
CPU_THREADS=$(($(sysctl -n hw.ncpu) - 1))
if [ $CPU_THREADS -lt 1 ]; then
    CPU_THREADS=1
fi
MAXFOUND=10000
AUTOSAVE_INTERVAL=60

echo "=== Проверка зеркального диапазона (28-29% puzzle71) ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "PROGRESS_FILE=$PROGRESS_FILE"
echo "CPU_THREADS=$CPU_THREADS"
echo "PATTERN=$PATTERN"
echo ""

# Проверка файла сегментов
if [ ! -f "$SEG_FILE" ]; then
    echo "Создание сегментов..."
    python3 generate_segments_mirror.py > "$SEG_FILE" 2>&1
fi

if [ ! -s "$SEG_FILE" ] || ! grep -q "^abs " "$SEG_FILE"; then
    echo "Ошибка: не удалось создать сегменты"
    exit 1
fi

SEG_COUNT=$(grep -c "^abs " "$SEG_FILE")
echo "✓ Создано $SEG_COUNT сегментов"

# Проверка VanitySearch
if [ ! -f "./VanitySearch" ]; then
    echo "Ошибка: VanitySearch не найден! Сначала соберите проект: make"
    exit 1
fi

# Автоматический resume если есть progress файл
RESUME_FLAG=""
if [ -f "$PROGRESS_FILE" ]; then
    echo "ℹ Найден файл прогресса, будет использован -resume"
    RESUME_FLAG="-resume"
fi

echo "✓ Запуск проверки..."
echo ""

# Запуск (можно без nohup, т.к. это относительно быстро)
./VanitySearch \
    -seg "$SEG_FILE" \
    -bits $BITS \
    $RESUME_FLAG \
    -progress "$PROGRESS_FILE" \
    -autosave $AUTOSAVE_INTERVAL \
    -t $CPU_THREADS \
    -m $MAXFOUND \
    -o "$OUT_FILE" \
    "$PATTERN" \
    > "$LOG_FILE" 2>&1

echo "✓ Завершено. Проверьте результаты:"
echo "  Найденные: cat $OUT_FILE"
echo "  Лог: tail -30 $LOG_FILE"

