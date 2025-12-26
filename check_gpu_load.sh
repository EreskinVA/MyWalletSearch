#!/bin/bash
# Скрипт для проверки загрузки GPU и рекомендаций по параметру -g

echo "=========================================="
echo "📊 Мониторинг GPU для VanitySearch"
echo "=========================================="
echo ""

# Проверка, запущен ли VanitySearch
if pgrep -f VanitySearch > /dev/null; then
    echo "✅ VanitySearch запущен (PID: $(pgrep -f VanitySearch | head -1))"
else
    echo "⚠️  VanitySearch НЕ запущен (метрики будут нулевыми)"
fi
echo ""

# Проверка доступности nvidia-smi
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ nvidia-smi не найден. Установите NVIDIA драйверы."
    exit 1
fi

# Получаем метрики
GPU_INFO=$(nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,power.draw,power.limit,temperature.gpu --format=csv,noheader,nounits)
GPU_UTIL=$(echo "$GPU_INFO" | awk -F', ' '{print $3}')
MEM_USED=$(echo "$GPU_INFO" | awk -F', ' '{print $4}')
MEM_TOTAL=$(echo "$GPU_INFO" | awk -F', ' '{print $5}')
POWER_DRAW=$(echo "$GPU_INFO" | awk -F', ' '{print $6}')
POWER_LIMIT=$(echo "$GPU_INFO" | awk -F', ' '{print $7}')
TEMP=$(echo "$GPU_INFO" | awk -F', ' '{print $8}')

# Вычисляем процент использования памяти
MEM_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED/$MEM_TOTAL)*100}")

echo "🔍 Текущие метрики GPU:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "GPU Utilization:    ${GPU_UTIL}%"
echo "Memory Usage:       ${MEM_USED} MiB / ${MEM_TOTAL} MiB (${MEM_PERCENT}%)"
echo "Power Draw:         ${POWER_DRAW} W / ${POWER_LIMIT} W"
echo "Temperature:        ${TEMP}°C"
echo ""

# Анализ и рекомендации
echo "💡 Анализ и рекомендации:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CAN_INCREASE=false
RECOMMENDATIONS=()

# Проверка GPU Utilization
if [ "$GPU_UTIL" -lt 90 ]; then
    CAN_INCREASE=true
    RECOMMENDATIONS+=("✅ GPU-Util ${GPU_UTIL}% < 90% → можно увеличить -g")
else
    RECOMMENDATIONS+=("⚠️  GPU-Util ${GPU_UTIL}% ≥ 90% → оптимально")
fi

# Проверка памяти
MEM_THRESHOLD=80
MEM_COMPARE=$(awk "BEGIN {if ($MEM_PERCENT < $MEM_THRESHOLD) print 1; else print 0}")
if [ "$MEM_COMPARE" -eq 1 ]; then
    CAN_INCREASE=true
    RECOMMENDATIONS+=("✅ Память ${MEM_PERCENT}% < ${MEM_THRESHOLD}% → есть запас для увеличения")
else
    RECOMMENDATIONS+=("⚠️  Память ${MEM_PERCENT}% ≥ ${MEM_THRESHOLD}% → близко к лимиту")
fi

# Проверка мощности
POWER_PERCENT=$(awk "BEGIN {printf \"%.0f\", ($POWER_DRAW/$POWER_LIMIT)*100}")
if [ "$POWER_PERCENT" -lt 85 ]; then
    CAN_INCREASE=true
    RECOMMENDATIONS+=("✅ Мощность ${POWER_PERCENT}% < 85% → есть запас")
else
    RECOMMENDATIONS+=("⚠️  Мощность ${POWER_PERCENT}% ≥ 85% → близко к TDP")
fi

# Вывод рекомендаций
for rec in "${RECOMMENDATIONS[@]}"; do
    echo "$rec"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Финальная рекомендация
if [ "$CAN_INCREASE" = true ]; then
    echo ""
    echo "✅ ВЫВОД: Можно попробовать увеличить -g"
    echo ""
    echo "Рекомендации:"
    echo "  1. Текущий:  -g 64,128"
    echo "  2. Попробуйте: -g 128,128  (увеличить X в 2 раза)"
    echo "  3. Или:      -g 96,128   (увеличить X в 1.5 раза)"
    echo ""
    echo "⚠️  ВАЖНО: После изменения проверьте:"
    echo "  • Логи на наличие 'items lost' (переполнение буфера)"
    echo "  • Если 'items lost' → увеличьте -m или уменьшите -g"
    echo "  • GPU-Util должен остаться ≥ 85%"
else
    echo ""
    echo "⚠️  ВЫВОД: Текущая конфигурация оптимальна или близка к лимиту"
    echo ""
    echo "Рекомендации:"
    echo "  • Оставьте -g 64,128"
    echo "  • Если нужна большая производительность → уменьшите количество сегментов"
fi

echo ""
echo "=========================================="
echo "📝 Как проверить 'items lost' в логах:"
echo "   tail -f log_*.log | grep -i 'items lost'"
echo ""
echo "🔄 Мониторинг в реальном времени:"
echo "   watch -n 1 nvidia-smi"
echo "   (или: watch -n 1 ./check_gpu_load.sh)"
echo "=========================================="

