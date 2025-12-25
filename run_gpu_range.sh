#!/bin/bash
set -euo pipefail

# GPU запуск VanitySearch для диапазона из seg_gpu_range.txt
# Ожидается, что вы на сервере в каталоге с бинарником ./VanitySearch

SEG_FILE="seg_gpu_range.txt"
OUT_FILE="out_gpu_range.txt"
LOG_FILE="log_gpu_range.log"

# Параметры GPU (рекомендованные для RTX4090 из предыдущих тестов)
GPU_ID="${GPU_ID:-0}"
GRID="${GRID:-64,128}"
CPU_THREADS="${CPU_THREADS:-2}"
MAXFOUND="${MAXFOUND:-1000000}"
BITS="${BITS:-71}"
PATTERN="${PATTERN:-1PWo3JeB9jr}"

echo "=== GPU range run ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "GPU_ID=$GPU_ID GRID=$GRID CPU_THREADS=$CPU_THREADS MAXFOUND=$MAXFOUND BITS=$BITS"
echo "PATTERN=$PATTERN"

# Подготовка файлов
: > "$OUT_FILE"
: > "$LOG_FILE"

nohup bash -c "./VanitySearch -seg \"$SEG_FILE\" -bits \"$BITS\" -gpu -gpuId \"$GPU_ID\" -g \"$GRID\" -t \"$CPU_THREADS\" -m \"$MAXFOUND\" -o \"$OUT_FILE\" \"$PATTERN\" > \"$LOG_FILE\" 2>&1" &

PID=$!
echo "Запущено. PID=$PID"
echo "Проверка: tail -f $LOG_FILE"


