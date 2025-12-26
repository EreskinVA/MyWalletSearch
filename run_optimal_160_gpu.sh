#!/bin/bash
# GPU поиск на сервере: ОПТИМИЗИРОВАННЫЙ диапазон 71-73%
# 160 сегментов, паттерн 1PWo3JeB9* (9 символов)
# ЦЕЛЬ: 1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU (Bitcoin Puzzle #71)

set -euo pipefail

# Параметры
SEG_FILE="seg_optimal_160_71_73.txt"
OUT_FILE="out_optimal_160_71_73.txt"
LOG_FILE="log_optimal_160_71_73.log"
PROGRESS_FILE="progress_optimal_160_71_73.dat"
PATTERN="1PWo3JeB9*"  # 9 символов - высокая специфичность
BITS=71
GPU_ID=0  # Измените на нужный GPU или используйте несколько: 0,1,2,3
GRID="128,256"  # Для RTX 4090. Если OOM, уменьшите: 64,128 или 32,128
CPU_THREADS=2
MAXFOUND=5000000  # Большой буфер для находок
AUTOSAVE_INTERVAL=300  # Автосохранение каждые 5 минут

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  🎯 ОПТИМИЗИРОВАННЫЙ ПОИСК PUZZLE #71                                      ║"
echo "║  Диапазон: 71-73% (где найдены 1PWo3JeB6, 1PWo3JeBj)                      ║"
echo "║  160 сегментов для максимального покрытия                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "=== Конфигурация ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "PROGRESS_FILE=$PROGRESS_FILE"
echo "PATTERN=$PATTERN"
echo "BITS=$BITS"
echo "GPU_ID=$GPU_ID"
echo "GRID=$GRID"
echo "CPU_THREADS=$CPU_THREADS"
echo "MAXFOUND=$MAXFOUND"
echo "AUTOSAVE_INTERVAL=${AUTOSAVE_INTERVAL} сек"
echo ""

# Проверка файла сегментов
if [ ! -f "$SEG_FILE" ]; then
    echo "❌ Ошибка: файл сегментов $SEG_FILE не найден!"
    echo "   Скопируйте seg_optimal_160_71_73.txt на сервер"
    exit 1
fi

# Проверка VanitySearch
if [ ! -f "./VanitySearch" ]; then
    echo "❌ Ошибка: VanitySearch не найден!"
    echo "   Соберите проект: make clean && make gpu=1 CCAP=8.9 all -j\"\$(nproc)\""
    exit 1
fi

# Автоматический resume если есть progress файл
RESUME_FLAG=""
if [ -f "$PROGRESS_FILE" ]; then
    echo "ℹ️  Найден файл прогресса, будет использован -resume"
    RESUME_FLAG="-resume"
fi

echo ""
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
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  📊 ПОЛЕЗНЫЕ КОМАНДЫ                                                       ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Посмотреть лог (последние 50 строк):"
echo "   tail -50 $LOG_FILE"
echo ""
echo "🔄 Следить за логом в реальном времени:"
echo "   tail -f $LOG_FILE"
echo ""
echo "📈 Посмотреть прогресс (детальный):"
echo "   python3 show_segment_progress.py $SEG_FILE $PROGRESS_FILE $OUT_FILE"
echo ""
echo "📊 Посмотреть прогресс (упрощённый):"
echo "   ./show_segment_progress_simple.sh $SEG_FILE $PROGRESS_FILE"
echo ""
echo "🔍 Посчитать найденные адреса:"
echo "   grep -c 'PubAddress:' $OUT_FILE 2>/dev/null || echo '0'"
echo ""
echo "🎯 Проверить, найден ли целевой адрес:"
echo "   grep '1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU' $OUT_FILE"
echo ""
echo "🔴 Остановить поиск:"
echo "   pkill -f 'VanitySearch.*-seg.*$SEG_FILE'"
echo "   Или: kill $PID"
echo ""
echo "💾 Сделать резервную копию прогресса:"
echo "   cp $PROGRESS_FILE ${PROGRESS_FILE}.backup.\$(date +%Y%m%d_%H%M%S)"
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  ВАЖНЫЕ ПРИМЕЧАНИЯ                                                     ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "1. 🔥 Если видите OOM (out of memory), уменьшите -g:"
echo "      Попробуйте: -g 64,128 или -g 32,128"
echo ""
echo "2. 📊 Мониторьте GPU:"
echo "      nvidia-smi -l 1  # обновление каждую секунду"
echo ""
echo "3. 💡 Ожидаемая скорость:"
echo "      RTX 4090: ~1-2 GKey/s"
echo "      RTX 3090: ~0.8-1.5 GKey/s"
echo ""
echo "4. ⏱️  Время покрытия диапазона (оценка):"
echo "      При 1 GKey/s: несколько недель-месяцев"
echo "      При 10 GKey/s (10 GPU): несколько дней-недель"
echo ""
echo "5. 🎯 Этот диапазон ОПТИМАЛЬНЫЙ:"
echo "      Найденные адреса 1PWo3JeB6 и 1PWo3JeBj указывают,"
echo "      что 1PWo3JeB9 находится в этом диапазоне!"
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  🚀 УДАЧИ В ПОИСКЕ!                                                        ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

