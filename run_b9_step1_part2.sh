#!/bin/bash
# Step 1 Part 2: Запуск CPU поиска с паттерном 1PWo3JeB9 (сегменты 9-16)

set -euo pipefail

# Параметры
SEG_FILE="seg_b9_step1_part2.txt"
OUT_FILE="out_b9_step1_part2.txt"
LOG_FILE="log_b9_step1_part2.log"
PROGRESS_FILE="progress_b9_step1_part2.dat"
PATTERN="1PWo3JeB9"
BITS=71
CPU_THREADS=$(($(sysctl -n hw.ncpu) - 1))
if [ $CPU_THREADS -lt 1 ]; then
    CPU_THREADS=1
fi
MAXFOUND=1000000
AUTOSAVE_INTERVAL=60

echo "=== Step 1 Part 2: CPU поиск паттерна $PATTERN (сегменты 9-16) ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "PROGRESS_FILE=$PROGRESS_FILE"
echo "CPU_THREADS=$CPU_THREADS"
echo "MAXFOUND=$MAXFOUND"
echo "AUTOSAVE_INTERVAL=${AUTOSAVE_INTERVAL} сек"
echo ""

# Проверка файла сегментов
if [ ! -f "$SEG_FILE" ]; then
    echo "Ошибка: файл сегментов $SEG_FILE не найден!"
    exit 1
fi

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

echo "✓ Запуск поиска..."
echo ""

# Запуск с nohup для работы в фоне
nohup ./VanitySearch \
    -seg "$SEG_FILE" \
    -bits $BITS \
    $RESUME_FLAG \
    -progress "$PROGRESS_FILE" \
    -autosave $AUTOSAVE_INTERVAL \
    -t $CPU_THREADS \
    -m $MAXFOUND \
    -o "$OUT_FILE" \
    "$PATTERN" \
    > "$LOG_FILE" 2>&1 &

PID=$!
echo "✓ Запущено. PID=$PID"
echo ""
echo "Полезные команды:"
echo "  Посмотреть лог: tail -f $LOG_FILE"
echo "  Посмотреть прогресс: python3 show_segment_progress.py $SEG_FILE $PROGRESS_FILE $OUT_FILE"
echo "  Посчитать найденные: wc -l $OUT_FILE"
echo "  Остановить: pkill -f 'VanitySearch.*-seg.*$SEG_FILE'"

