#!/bin/bash
# Простой shell-скрипт для просмотра прогресса (без Python)

SEG_FILE="${1:-seg_gpu_range.txt}"
PROGRESS_FILE="${2:-progress_gpu_range.dat}"

if [ ! -f "$PROGRESS_FILE" ]; then
    echo "Ошибка: файл прогресса не найден: $PROGRESS_FILE"
    exit 1
fi

echo "========================================"
echo "Прогресс поиска"
echo "========================================"
echo "Файл конфигурации: $SEG_FILE"
echo "Файл прогресса:    $PROGRESS_FILE"
echo ""

# Общая информация
if grep -q "VANITYSEARCH_PROGRESS" "$PROGRESS_FILE"; then
    total_keys=$(grep "^TotalKeysChecked=" "$PROGRESS_FILE" | cut -d= -f2)
    bit_range=$(grep "^BitRange=" "$PROGRESS_FILE" | cut -d= -f2)
    target=$(grep "^TargetAddress=" "$PROGRESS_FILE" | cut -d= -f2)
    
    echo "Битовый диапазон:  $bit_range"
    echo "Целевой адрес:     $target"
    echo "Всего проверено:   $total_keys ключей"
    echo ""
fi

# Сегменты
echo "Сегменты:"
echo "----------------------------------------"
echo ""

in_segment=false
segment_num=0

while IFS= read -r line; do
    if [ "$line" = "SEGMENT_START" ]; then
        in_segment=true
        segment_num=$((segment_num + 1))
        name=""
        active=""
        keys_checked=""
        current_key=""
        continue
    elif [ "$line" = "SEGMENT_END" ]; then
        in_segment=false
        if [ -n "$name" ]; then
            printf "Сегмент %d: %-12s " "$segment_num" "$name"
            if [ "$active" = "1" ]; then
                printf "▶ Активен   "
            else
                printf "✓ Завершен  "
            fi
            printf "Ключей проверено: %s\n" "$keys_checked"
        fi
        continue
    fi
    
    if [ "$in_segment" = true ]; then
        if [[ $line == Name=* ]]; then
            name="${line#Name=}"
        elif [[ $line == Active=* ]]; then
            active="${line#Active=}"
        elif [[ $line == KeysChecked=* ]]; then
            keys_checked="${line#KeysChecked=}"
        elif [[ $line == CurrentKey=* ]]; then
            current_key="${line#CurrentKey=}"
        fi
    fi
done < "$PROGRESS_FILE"

echo ""
echo "----------------------------------------"
echo "Всего сегментов: $segment_num"

