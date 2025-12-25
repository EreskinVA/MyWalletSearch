#!/bin/bash
set -euo pipefail

# GPU запуск VanitySearch с автоматическим resume из progress файла (если он есть)

SEG_FILE="seg_gpu_range.txt"
OUT_FILE="out_gpu_range.txt"
LOG_FILE="log_gpu_range.log"
PROGRESS_FILE="progress_gpu_range.dat"

# Параметры GPU
GPU_ID="${GPU_ID:-0}"
GRID="${GRID:-64,128}"
CPU_THREADS="${CPU_THREADS:-2}"
MAXFOUND="${MAXFOUND:-1000000}"
BITS="${BITS:-71}"
PATTERN="${PATTERN:-1PWo3JeB9jr}"
AUTOSAVE_INTERVAL="${AUTOSAVE_INTERVAL:-120}"

echo "=== GPU range run (с автоматическим resume) ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "PROGRESS_FILE=$PROGRESS_FILE"
echo "GPU_ID=$GPU_ID GRID=$GRID CPU_THREADS=$CPU_THREADS MAXFOUND=$MAXFOUND BITS=$BITS"
echo "PATTERN=$PATTERN"
echo "AUTOSAVE_INTERVAL=$AUTOSAVE_INTERVAL сек"
echo ""

# Проверяем наличие файла прогресса
RESUME_FLAG=""
if [ -f "$PROGRESS_FILE" ]; then
    echo "✓ Найден файл прогресса: $PROGRESS_FILE"
    echo "  Будет использован режим -resume (продолжение с сохранённой позиции)"
    RESUME_FLAG="-resume"
else
    echo "⚠ Файл прогресса не найден: $PROGRESS_FILE"
    echo "  Поиск начнётся сначала (новый прогресс будет сохранён)"
fi
echo ""

# Подготовка файлов (НЕ перезаписываем OUT_FILE и LOG_FILE если они уже есть с данными)
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
echo "Запущено. PID=$PID"
echo "Проверка: tail -f $LOG_FILE"
echo ""
echo "Полезные команды:"
echo "  Посмотреть прогресс: python3 show_segment_progress.py $SEG_FILE $PROGRESS_FILE"
echo "  Или упрощённо:       ./show_segment_progress_simple.sh $SEG_FILE $PROGRESS_FILE"

