#!/bin/bash
# Проверка соседних ключей (±256 от найденных)
# Согласно анализу п. 4.1: off-by-one ошибки

set -euo pipefail

# Параметры
OUT_FILES="out_cpu_p1.txt out_cpu_p2.txt out_cpu_p3.txt"  # Файлы с найденными ключами
SEG_FILE="seg_neighbors.txt"
OUT_FILE="out_neighbors.txt"
LOG_FILE="log_neighbors.log"
PROGRESS_FILE="progress_neighbors.dat"
PATTERN="1PWo3JeB9jr"  # Целевой паттерн (может быть любой)
BITS=71
CPU_THREADS=$(($(sysctl -n hw.ncpu) - 1))
if [ $CPU_THREADS -lt 1 ]; then
    CPU_THREADS=1
fi
MAXFOUND=10000
AUTOSAVE_INTERVAL=10  # Короткий интервал, т.к. это быстро

echo "=== Проверка соседних ключей (±256 от найденных) ==="
echo ""

# Генерация сегментов из найденных ключей
echo "Генерация сегментов из найденных ключей..."
python3 generate_segments_neighbors.py $OUT_FILES > "$SEG_FILE" 2>&1

if [ ! -s "$SEG_FILE" ] || ! grep -q "^abs " "$SEG_FILE"; then
    echo "Ошибка: не удалось создать сегменты или не найдено ключей"
    echo "Проверьте что в $OUT_FILES есть строки 'PuzzleKeyAbs (DEC): ...'"
    exit 1
fi

SEG_COUNT=$(grep -c "^abs " "$SEG_FILE")
echo "✓ Создано $SEG_COUNT сегментов"

# Проверка VanitySearch
if [ ! -f "./VanitySearch" ]; then
    echo "Ошибка: VanitySearch не найден! Сначала соберите проект: make"
    exit 1
fi

# Оценка времени выполнения
TOTAL_KEYS=$((SEG_COUNT * 513))  # 513 = 256*2+1
CPU_SPEED=1000000  # 1 Mkey/s (консервативная оценка)
ESTIMATED_TIME=$((TOTAL_KEYS / CPU_SPEED))

echo "Всего ключей для проверки: ~$TOTAL_KEYS"
if [ $ESTIMATED_TIME -lt 1 ]; then
    echo "Оценка времени: < 1 сек (очень быстро!)"
else
    echo "Оценка времени: ~$ESTIMATED_TIME сек"
fi
echo ""

# Автоматический resume если есть progress файл
RESUME_FLAG=""
if [ -f "$PROGRESS_FILE" ]; then
    echo "ℹ Найден файл прогресса, будет использован -resume"
    RESUME_FLAG="-resume"
fi

echo "✓ Запуск проверки..."
echo ""

# Запуск (можно без nohup, т.к. это быстро)
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
echo "  Лог: tail -20 $LOG_FILE"

