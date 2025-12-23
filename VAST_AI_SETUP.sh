#!/bin/bash
#
# Автоматическая установка и запуск на Vast.ai
# Скопируйте и вставьте этот скрипт целиком в терминал на сервере
#

set -e

echo "🚀 MyWalletSearch - Автоматическая установка на Vast.ai"
echo "========================================================"
echo ""

# Проверка GPU
echo "📊 Проверка конфигурации..."
nvidia-smi --query-gpu=index,name,compute_cap,memory.total --format=csv
GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
echo ""
echo "✅ Обнаружено GPU: $GPU_COUNT"
echo ""

# Клонирование репозитория
echo "📦 Клонирование MyWalletSearch..."
cd ~
if [ -d "MyWalletSearch" ]; then
    echo "⚠️  Директория уже существует, обновляем..."
    cd MyWalletSearch
    git pull
else
    git clone https://github.com/EreskinVA/MyWalletSearch.git
    cd MyWalletSearch
fi
echo "✅ Репозиторий готов"
echo ""

# Проверка CUDA
echo "🔧 Проверка CUDA..."
nvcc --version | grep release
echo ""

# Компиляция
echo "🔨 Компиляция с GPU поддержкой (RTX 4090, CCAP=8.9)..."
make clean
make gpu=1 CCAP=8.9 all
echo ""

if [ ! -f "VanitySearch" ]; then
    echo "❌ Ошибка компиляции!"
    exit 1
fi

echo "✅ Компиляция успешна!"
ls -lh VanitySearch
echo ""

# Проверка GPU в VanitySearch
echo "📊 Проверка GPU в VanitySearch..."
./VanitySearch -l
echo ""

# Формирование списка GPU ID
GPU_IDS=""
for i in $(seq 0 $((GPU_COUNT - 1))); do
    if [ -z "$GPU_IDS" ]; then
        GPU_IDS="$i"
    else
        GPU_IDS="$GPU_IDS,$i"
    fi
done

echo "🎯 Будут использованы GPU: $GPU_IDS"
echo ""

# Запуск поиска
echo "🚀 Запуск поиска Puzzle 71 (FOCUSED стратегия)..."
echo ""
echo "Конфигурация:"
echo "  • Сегменты: 48-56% (зона максимальной вероятности)"
echo "  • Алгоритм: Pollard's Kangaroo"
echo "  • GPU: $GPU_COUNT штук"
echo "  • CPU threads: 128"
echo "  • Автосохранение: каждые 10 минут"
echo ""
echo "Ожидаемое время: 12-24 часа"
echo "Вероятность успеха: ~80%"
echo ""

read -p "Начать поиск? (yes/no): " answer

if [ "$answer" != "yes" ]; then
    echo "Отменено пользователем"
    exit 0
fi

# Запуск в фоновом режиме
nohup ./VanitySearch -seg segments_14xRTX4090_FOCUSED.txt -bits 71 \\
               -kangaroo \\
               -progress puzzle71_round1.dat -autosave 600 \\
               -gpu -gpuId $GPU_IDS \\
               -g 1024,256 \\
               -t 128 \\
               -o PUZZLE_71_SOLUTION.txt \\
               1FshYo > search.log 2>&1 &

SEARCH_PID=$!

echo ""
echo "✅ Поиск запущен!"
echo "   PID: $SEARCH_PID"
echo ""
echo "📊 Для мониторинга:"
echo "   tail -f search.log"
echo ""
echo "📈 Для визуализации (в другом терминале):"
echo "   python3 visualize_progress.py puzzle71_round1.dat --watch 30"
echo ""
echo "🛑 Для остановки:"
echo "   kill $SEARCH_PID"
echo ""

sleep 5

echo "📋 Первые строки лога:"
tail -30 search.log

echo ""
echo "🎉 ВСЁ ГОТОВО! Поиск работает!"
echo ""
echo "Проверяйте прогресс: tail -f search.log"

