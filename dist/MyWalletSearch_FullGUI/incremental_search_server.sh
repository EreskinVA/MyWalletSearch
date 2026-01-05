#!/bin/bash
# Инкрементальный поиск для сервера с GPU

TARGET="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
CURRENT_PREFIX="1PWo3Je"
CURRENT_SUFFIX="zXU"
SEARCH_TIME=300  # 5 минут для GPU
BITS=71
SEGMENTS_FILE="segments_puzzle71.txt"
OUTPUT_FILE="incremental_results.txt"
PROGRESS_FILE="incremental_progress_gpu.dat"
LOG_FILE="incremental_search_gpu.log"
MAX_ITERATIONS=20

echo "=========================================="
echo "🚀 Инкрементальный поиск на GPU"
echo "=========================================="
echo "🎯 Целевой адрес: $TARGET"
echo "📋 Текущий паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
echo "⏱️  Время поиска: ${SEARCH_TIME} сек (${SEARCH_TIME}/60 мин)"
echo "🔄 Максимум итераций: $MAX_ITERATIONS"
echo "=========================================="
echo

# Функция для анализа результатов
analyze_results() {
    local output_file="$1"
    local best_score=0
    local best_match=""
    
    if [ ! -f "$output_file" ] || [ ! -s "$output_file" ]; then
        echo "⚠️  Файл результатов пуст"
        return 1
    fi
    
    echo "📊 Анализ найденных адресов:"
    echo "----------------------------------------"
    
    while IFS= read -r line; do
        if [[ $line =~ ^PubAddress:[[:space:]]+(1[A-Za-z0-9]+) ]]; then
            local found_addr="${BASH_REMATCH[1]}"
            local score=0
            
            for ((i=0; i<${#found_addr} && i<${#TARGET}; i++)); do
                if [ "${found_addr:$i:1}" == "${TARGET:$i:1}" ]; then
                    ((score++))
                else
                    break
                fi
            done
            
            if [ $score -gt $best_score ]; then
                best_score=$score
                best_match="$found_addr"
            fi
            
            echo "  ✓ $found_addr (совпадение: $score символов)"
        fi
    done < "$output_file"
    
    echo "----------------------------------------"
    if [ $best_score -gt 0 ]; then
        echo "✅ Лучшее совпадение: $best_match ($best_score символов)"
        echo "$best_score"
        return 0
    fi
    
    return 1
}

# Основной цикл
iteration=1
while [ $iteration -le $MAX_ITERATIONS ]; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 Итерация $iteration/$MAX_ITERATIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    
    local pattern="${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
    echo "🔍 Поиск: $pattern"
    echo "⏱️  Время: ${SEARCH_TIME} секунд"
    echo
    
    # Очистить предыдущие результаты
    > "$OUTPUT_FILE"
    
    # Запустить поиск на GPU
    timeout ${SEARCH_TIME}s ./VanitySearch \
        -seg "$SEGMENTS_FILE" \
        -bits $BITS \
        -kangaroo \
        -progress "$PROGRESS_FILE" \
        -autosave 60 \
        -gpu \
        -gpuId 0 \
        -g 512,128 \
        -t 8 \
        -o "$OUTPUT_FILE" \
        "$pattern" > "$LOG_FILE" 2>&1
    
    local exit_code=$?
    
    echo
    if [ $exit_code -eq 124 ]; then
        echo "⏱️  Поиск завершен по таймауту"
    elif [ $exit_code -eq 0 ]; then
        echo "✅ Поиск завершен успешно"
    else
        echo "⚠️  Поиск завершен с кодом: $exit_code"
    fi
    
    # Анализ результатов
    echo
    best_score=$(analyze_results "$OUTPUT_FILE")
    
    if [ $? -eq 0 ] && [ -n "$best_score" ]; then
        echo
        echo "💡 Анализ совпадения:"
        
        # Определить следующий шаг
        if [ $best_score -lt ${#TARGET} ]; then
            local next_char="${TARGET:$best_score:1}"
            local new_prefix="${TARGET:0:$((best_score + 1))}"
            
            # Проверить, нужно ли обновить префикс или суффикс
            local prefix_len=${#CURRENT_PREFIX}
            local suffix_start=$((${#TARGET} - ${#CURRENT_SUFFIX}))
            
            if [ $best_score -lt $suffix_start ]; then
                # Увеличиваем префикс
                echo "   Следующий символ: '$next_char' (позиция $best_score)"
                echo "   Новый префикс: $new_prefix"
                CURRENT_PREFIX="$new_prefix"
            else
                # Увеличиваем суффикс
                local new_suffix_len=$((${#TARGET} - $best_score))
                local new_suffix="${TARGET: -$new_suffix_len:}"
                echo "   Новый суффикс: *$new_suffix"
                CURRENT_SUFFIX="$new_suffix"
            fi
            
            echo "   Обновленный паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
        else
            echo "🎉 Целевой адрес найден!"
            break
        fi
    else
        echo "⚠️  Совпадений не найдено, продолжаем с текущим паттерном"
    fi
    
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    
    ((iteration++))
    sleep 5
done

echo
echo "=========================================="
echo "📋 Итоговый отчет"
echo "=========================================="
echo "🎯 Целевой адрес: $TARGET"
echo "📋 Финальный паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
echo "📁 Результаты: $OUTPUT_FILE"
echo "📝 Лог: $LOG_FILE"
echo "=========================================="

