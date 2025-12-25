#!/bin/bash
set -euo pipefail

# GPU запуск VanitySearch для диапазона 69-72% от puzzle 71

SEG_FILE="seg_puzzle71_69_72.txt"
OUT_FILE="out_puzzle71_69_72.txt"
LOG_FILE="log_puzzle71_69_72.log"
PROGRESS_FILE="progress_puzzle71_69_72.dat"

# Параметры GPU
GPU_ID="${GPU_ID:-0}"
GRID="${GRID:-64,128}"
CPU_THREADS="${CPU_THREADS:-2}"
MAXFOUND="${MAXFOUND:-1000000}"
BITS="${BITS:-71}"
PATTERN="${PATTERN:-1PWo3JeB}"  # Префикс для puzzle 71
AUTOSAVE_INTERVAL="${AUTOSAVE_INTERVAL:-120}"  # 2 минуты

echo "=== GPU запуск: Puzzle 71, 69-72% диапазон ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "PROGRESS_FILE=$PROGRESS_FILE"
echo "GPU_ID=$GPU_ID GRID=$GRID CPU_THREADS=$CPU_THREADS MAXFOUND=$MAXFOUND BITS=$BITS"
echo "PATTERN=$PATTERN"
echo "AUTOSAVE_INTERVAL=$AUTOSAVE_INTERVAL сек"
echo ""

# Проверяем наличие файла сегментов
if [ ! -f "$SEG_FILE" ]; then
    echo "Ошибка: файл сегментов не найден: $SEG_FILE"
    exit 1
fi

# Проверяем наличие файла прогресса для resume
RESUME_FLAG=""
if [ -f "$PROGRESS_FILE" ]; then
    echo "✓ Найден файл прогресса: $PROGRESS_FILE"
    echo "  Будет использован режим -resume (продолжение с сохранённой позиции)"
    RESUME_FLAG="-resume"
else
    echo "ℹ Файл прогресса не найден, поиск начнётся сначала"
fi
echo ""

# Подготовка файлов (НЕ перезаписываем если уже есть данные)
if [ ! -f "$OUT_FILE" ]; then
    : > "$OUT_FILE"
fi
if [ ! -f "$LOG_FILE" ]; then
    : > "$LOG_FILE"
fi

# Строим команду
CMD="./VanitySearch -seg \"$SEG_FILE\" -bits \"$BITS\" -gpu -gpuId \"$GPU_ID\" -g \"$GRID\" -t \"$CPU_THREADS\" -m \"$MAXFOUND\" -progress \"$PROGRESS_FILE\" -autosave \"$AUTOSAVE_INTERVAL\" -o \"$OUT_FILE\" \"$PATTERN\""

# Добавляем -resume если файл прогресса существует
if [ -n "$RESUME_FLAG" ]; then
    CMD="$CMD $RESUME_FLAG"
fi

nohup bash -c "$CMD > \"$LOG_FILE\" 2>&1" &

PID=$!
echo "✓ Запущено. PID=$PID"
echo ""
echo "Полезные команды:"
echo "  Посмотреть лог:        tail -f $LOG_FILE"
echo "  Посмотреть прогресс:   python3 show_segment_progress.py $SEG_FILE $PROGRESS_FILE"
echo "  Или упрощённо:         ./show_segment_progress_simple.sh $SEG_FILE $PROGRESS_FILE"
echo "  Посчитать найденные:   wc -l $OUT_FILE"
echo "  Остановить:            ./stop_search.sh"

