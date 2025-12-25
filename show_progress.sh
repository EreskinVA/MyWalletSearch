#!/bin/bash
# Скрипт для просмотра прогресса поиска

PROGRESS_FILE="${1:-progress_gpu_range.dat}"
LOG_FILE="${2:-log_gpu_range.log}"

echo "=== Прогресс поиска ==="
echo ""

# 1. Из лога - последняя строка статуса
if [ -f "$LOG_FILE" ]; then
    echo "--- Последний статус из лога ---"
    tail -n 1 "$LOG_FILE" 2>/dev/null | grep -o '\[.*\]' | head -1 || echo "Статус не найден"
    echo ""
    
    # Прогресс по сегментам
    echo "--- Прогресс по сегментам (последнее сообщение) ---"
    grep "\[ProgressManager\] Общий прогресс" "$LOG_FILE" 2>/dev/null | tail -1 || echo "Прогресс по сегментам не найден"
    echo ""
    
    # Сколько ключей проверено (Total 2^XX)
    echo "--- Проверено ключей (из последней строки) ---"
    last_line=$(tail -n 1 "$LOG_FILE" 2>/dev/null)
    if echo "$last_line" | grep -q "Total 2^"; then
        exp=$(echo "$last_line" | grep -oP 'Total 2\^\K[0-9.]+')
        if [ -n "$exp" ]; then
            # Python для вычисления 2^exp
            keys=$(python3 -c "print(f'{2**$exp:.2e}')" 2>/dev/null || echo "N/A")
            echo "Total: 2^$exp ≈ $keys ключей"
        fi
    else
        echo "Информация о Total не найдена"
    fi
    echo ""
fi

# 2. Из progress файла (если есть)
if [ -f "$PROGRESS_FILE" ]; then
    echo "--- Детали из progress файла ---"
    if grep -q "VANITYSEARCH_PROGRESS" "$PROGRESS_FILE" 2>/dev/null; then
        total_keys=$(grep "^TotalKeysChecked=" "$PROGRESS_FILE" 2>/dev/null | cut -d= -f2)
        if [ -n "$total_keys" ]; then
            echo "Всего ключей проверено: $total_keys"
        fi
        
        bit_range=$(grep "^BitRange=" "$PROGRESS_FILE" 2>/dev/null | cut -d= -f2)
        if [ -n "$bit_range" ]; then
            echo "Битовый диапазон: $bit_range"
        fi
        
        seg_count=$(grep -c "^SegmentName=" "$PROGRESS_FILE" 2>/dev/null || echo "0")
        if [ "$seg_count" -gt 0 ]; then
            echo "Сегментов в файле: $seg_count"
        fi
    else
        echo "Файл прогресса не найден или неверный формат"
    fi
else
    echo "--- Файл прогресса не найден: $PROGRESS_FILE ---"
    echo "   (прогресс не сохраняется, используйте -progress в команде запуска)"
fi

echo ""
echo "=== Полезные команды ==="
echo "  Смотреть лог в реальном времени: tail -f $LOG_FILE"
echo "  Проверить процесс: pgrep -fl VanitySearch"
echo "  Посчитать найденные: ./count_found_gpu_range.sh"

