#!/bin/bash
# GPU поиск на сервере: паттерн 1PWo3JeB (8 символов) на широком диапазоне
# Согласно анализу: GPU-фаза с более широким паттерном

set -euo pipefail

# Параметры
SEG_FILE="seg_gpu_b9_wide.txt"
OUT_FILE="out_gpu_b9_wide.txt"
LOG_FILE="log_gpu_b9_wide.log"
PROGRESS_FILE="progress_gpu_b9_wide.dat"
PATTERN="1PWo3JeB"
BITS=71
GPU_ID=0
GRID="64,128"  # RTX 4090: можно попробовать больше, если не OOM
CPU_THREADS=2
MAXFOUND=2000000
AUTOSAVE_INTERVAL=120

echo "=== GPU широкий поиск: паттерн $PATTERN (8 символов) ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "PROGRESS_FILE=$PROGRESS_FILE"
echo "GPU_ID=$GPU_ID"
echo "GRID=$GRID"
echo "CPU_THREADS=$CPU_THREADS"
echo "MAXFOUND=$MAXFOUND"
echo "AUTOSAVE_INTERVAL=${AUTOSAVE_INTERVAL} сек"
echo ""

# Проверка файла сегментов
if [ ! -f "$SEG_FILE" ]; then
    echo "Ошибка: файл сегментов $SEG_FILE не найден!"
    echo "Создайте его на сервере: python3 generate_segments_gpu_b9_wide.py > $SEG_FILE"
    exit 1
fi

# Проверка VanitySearch
if [ ! -f "./VanitySearch" ]; then
    echo "Ошибка: VanitySearch не найден! Сначала соберите проект: make clean && make gpu=1 CCAP=8.9 all -j\"\$(nproc)\""
    exit 1
fi

# Автоматический resume если есть progress файл
RESUME_FLAG=""
if [ -f "$PROGRESS_FILE" ]; then
    echo "ℹ Найден файл прогресса, будет использован -resume"
    RESUME_FLAG="-resume"
fi

echo "✓ Запуск GPU поиска..."
echo ""

# Запуск с nohup для работы в фоне
nohup ./VanitySearch \
    -seg "$SEG_FILE" \
    -bits $BITS \
    $RESUME_FLAG \
    -progress "$PROGRESS_FILE" \
    -autosave $AUTOSAVE_INTERVAL \
    -gpu \
    -gpuId $GPU_ID \
    -g $GRID \
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
echo "  Или упрощённо: ./show_segment_progress_simple.sh $SEG_FILE $PROGRESS_FILE"
echo "  Посчитать найденные: wc -l $OUT_FILE"
echo "  Остановить: pkill -f 'VanitySearch.*-seg.*$SEG_FILE'"
echo "  Или: kill $PID"
echo ""
echo "⚠ Примечание: Если видите OOM (out of memory), уменьшите -g:"
echo "   -g 32,128 или -g 16,128"

