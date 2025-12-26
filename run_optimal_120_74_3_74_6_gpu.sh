#!/bin/bash
# GPU поиск на сервере: УЗКИЙ диапазон 74.3-74.6%
# 120 сегментов, паттерн 1PWo3JeB (без wildcard для вывода Prob)
# ЦЕЛЬ: 1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU (Bitcoin Puzzle #71)
# ВАЖНО: Предыдущие процессы VanitySearch НЕ останавливаются!

set -eo pipefail  # Убрали -u чтобы не падать на неопределённых переменных

# Параметры
SEG_FILE="seg_optimal_120_74_3_74_6.txt"
OUT_FILE="out_optimal_120_74_3_74_6.txt"
LOG_FILE="log_optimal_120_74_3_74_6.log"
PROGRESS_FILE="progress_optimal_120_74_3_74_6.dat"
PATTERN="1PWo3JeB"  # БЕЗ звездочки - для вывода Prob!
BITS=71
GPU_ID=0  # Измените на нужный GPU или используйте несколько: 0,1,2,3
GRID="128,256"  # Для RTX 4090. Если OOM, уменьшите: 64,128 или 32,128
CPU_THREADS=2
MAXFOUND=5000000  # Большой буфер для находок
AUTOSAVE_INTERVAL=60  # Автосохранение каждые 1 минут

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  🎯 УЗКИЙ ПОИСК PUZZLE #71 (74.3-74.6%)                                    ║"
echo "║  120 сегментов, паттерн 1PWo3JeB (без wildcard)                            ║"
echo "║  ⚠️  Предыдущие процессы VanitySearch НЕ останавливаются!                   ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "=== Конфигурация ==="
echo "SEG_FILE=$SEG_FILE"
echo "OUT_FILE=$OUT_FILE"
echo "LOG_FILE=$LOG_FILE"
echo "PROGRESS_FILE=$PROGRESS_FILE"
echo "PATTERN=$PATTERN (БЕЗ wildcard для вывода Prob!)"
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
    echo "   Скопируйте seg_optimal_120_74_3_74_6.txt на сервер"
    exit 1
fi

# Проверка VanitySearch
if [ ! -f "./VanitySearch" ]; then
    echo "❌ Ошибка: VanitySearch не найден!"
    echo "   Соберите проект: make clean && make gpu=1 CCAP=8.9 all -j\"\$(nproc)\""
    exit 1
fi

# Проверка существующих процессов (НЕ останавливаем!)
EXISTING_PROCESSES=$(ps aux | grep '[V]anitySearch' 2>/dev/null | wc -l || echo "0")
if [ "$EXISTING_PROCESSES" -gt 0 ]; then
    echo "ℹ️  Найдено $EXISTING_PROCESSES активных процессов VanitySearch"
    echo "   Они продолжат работать параллельно с новым поиском"
    echo ""
    ps aux | grep '[V]anitySearch' 2>/dev/null | grep -v grep | head -5 || true
    echo ""
fi

# Автоматический resume если есть progress файл
RESUME_FLAG=""
if [ -f "$PROGRESS_FILE" ]; then
    echo "ℹ️  Найден файл прогресса, будет использован -resume"
    RESUME_FLAG="-resume"
else
    RESUME_FLAG=""  # Явно устанавливаем пустую строку
fi

echo "✓ Запуск нового GPU поиска (параллельно с существующими)..."
echo ""

# Запуск с nohup для работы в фоне
# Используем eval для правильной обработки пустого RESUME_FLAG
if [ -n "$RESUME_FLAG" ]; then
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
else
    nohup ./VanitySearch \
        -seg "$SEG_FILE" \
        -bits $BITS \
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
fi

PID=$!
sleep 2  # Даём процессу время запуститься

# Проверка, что процесс действительно запустился (универсальная проверка)
if kill -0 $PID 2>/dev/null || ps aux | grep -q "^[^ ]* *$PID " 2>/dev/null; then
    echo "✓ Запущено успешно. PID=$PID"
    echo ""
    echo "📋 Первые строки лога (проверка запуска):"
    tail -10 "$LOG_FILE" 2>/dev/null || echo "   (лог ещё пуст или недоступен)"
    echo ""
else
    echo "❌ Ошибка: Процесс не запустился или сразу завершился!"
    echo ""
    echo "📋 Содержимое лога (последние 50 строк):"
    tail -50 "$LOG_FILE" 2>/dev/null || echo "   (лог пуст или недоступен)"
    echo ""
    echo "🔍 Возможные причины:"
    echo "   - Ошибка в параметрах VanitySearch"
    echo "   - Проблема с GPU (OOM, драйверы, занят другим процессом)"
    echo "   - Ошибка в файле сегментов"
    echo "   - Недостаточно памяти"
    echo ""
    echo "💡 Попробуйте запустить вручную для диагностики:"
    echo "   ./VanitySearch -seg $SEG_FILE -bits $BITS -gpu -gpuId $GPU_ID -g $GRID -t $CPU_THREADS -m $MAXFOUND -o $OUT_FILE \"$PATTERN\""
    exit 1
fi
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
echo "📋 Список ВСЕХ процессов VanitySearch:"
echo "   ps aux | grep '[V]anitySearch'"
echo ""
echo "🔴 Остановить ТОЛЬКО этот процесс:"
echo "   kill $PID"
echo ""
echo "💾 Сделать резервную копию прогресса:"
echo "   cp $PROGRESS_FILE ${PROGRESS_FILE}.backup.\$(date +%Y%m%d_%H%M%S)"
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  ВАЖНЫЕ ПРИМЕЧАНИЯ                                                     ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "1. ✅ Паттерн '1PWo3JeB' БЕЗ звездочки - Prob будет выводиться!"
echo ""
echo "2. 🔥 Если видите OOM (out of memory), уменьшите -g:"
echo "      Попробуйте: -g 64,128 или -g 32,128"
echo ""
echo "3. 📊 Мониторьте GPU:"
echo "      nvidia-smi -l 1  # обновление каждую секунду"
echo ""
echo "4. 💡 Ожидаемая скорость:"
echo "      RTX 4090: ~1-2 GKey/s"
echo "      RTX 3090: ~0.8-1.5 GKey/s"
echo ""
echo "5. ⏱️  Время покрытия диапазона (оценка):"
echo "      При 1 GKey/s: несколько дней"
echo "      При 10 GKey/s (10 GPU): несколько часов"
echo ""
echo "6. 🎯 Этот диапазон УЗКИЙ (0.3%):"
echo "      Основано на анализе: найденные адреса в 74.5-76.5%"
echo "      Сужение до 74.3-74.6% для максимальной точности"
echo ""
echo "7. ⚠️  Предыдущие процессы НЕ остановлены:"
echo "      Они продолжат работать параллельно"
echo "      Используйте 'ps aux | grep VanitySearch' для мониторинга всех"
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  🚀 УДАЧИ В ПОИСКЕ!                                                        ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

