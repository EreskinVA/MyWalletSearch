#!/bin/bash
# Инкрементальный поиск с анализом результатов
# Постепенно увеличивает префикс/суффикс для приближения к целевому адресу

TARGET="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
CURRENT_PREFIX="1PWo3Je"
CURRENT_SUFFIX="zXU"
SEARCH_TIME=60  # Время поиска в секундах
BITS=71
SEGMENTS_FILE="segments_puzzle71.txt"
OUTPUT_FILE="incremental_results.txt"
PROGRESS_FILE="incremental_progress.dat"

echo "=========================================="
echo "Инкрементальный поиск Puzzle 71"
echo "=========================================="
echo "Целевой адрес: $TARGET"
echo "Текущий паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
echo "Время поиска: ${SEARCH_TIME} сек"
echo "=========================================="
echo

# Функция для анализа найденных адресов
analyze_results() {
    local output_file="$1"
    local target="$2"
    
    if [ ! -f "$output_file" ] || [ ! -s "$output_file" ]; then
        echo "⚠️  Файл результатов пуст или не найден"
        return 1
    fi
    
    echo "📊 Анализ найденных адресов:"
    echo "----------------------------------------"
    
    # Найти адреса, которые ближе всего к целевому
    local best_match=""
    local best_score=0
    
    while IFS= read -r line; do
        if [[ $line =~ ^PubAddress:[[:space:]]+(1[A-Za-z0-9]+) ]]; then
            local found_addr="${BASH_REMATCH[1]}"
            local score=0
            
            # Сравниваем с целевым адресом
            for ((i=0; i<${#found_addr} && i<${#target}; i++)); do
                if [ "${found_addr:$i:1}" == "${target:$i:1}" ]; then
                    ((score++))
                else
                    break
                fi
            done
            
            if [ $score -gt $best_score ]; then
                best_score=$score
                best_match="$found_addr"
            fi
            
            echo "  Найдено: $found_addr (совпадение: $score символов)"
        fi
    done < "$output_file"
    
    echo "----------------------------------------"
    if [ $best_score -gt 0 ]; then
        echo "✅ Лучшее совпадение: $best_match ($best_score символов)"
        echo "   Целевой адрес:     $target"
        
        # Предложить следующий шаг
        if [ $best_score -lt ${#target} ]; then
            local next_char_pos=$best_score
            local next_char="${target:$next_char_pos:1}"
            echo "   💡 Следующий символ для поиска: '$next_char' (позиция $next_char_pos)"
        fi
    else
        echo "❌ Совпадений не найдено"
    fi
    
    return 0
}

# Функция для предложения следующего шага
suggest_next_step() {
    local best_score=$1
    local current_prefix="$2"
    local current_suffix="$3"
    local target="$4"
    
    echo
    echo "💡 Рекомендации для следующего шага:"
    echo "----------------------------------------"
    
    if [ $best_score -lt ${#target} ]; then
        local next_char_pos=$best_score
        local next_char="${target:$next_char_pos:1}"
        
        # Определяем, увеличивать ли префикс или суффикс
        if [ $next_char_pos -lt $((${#target} - ${#current_suffix})) ]; then
            # Увеличиваем префикс
            local new_prefix="${current_prefix}${next_char}"
            echo "1. Увеличить префикс: ${new_prefix}*${current_suffix}"
            echo "   Команда: ./VanitySearch -seg $SEGMENTS_FILE -bits $BITS -kangaroo \\"
            echo "            -progress $PROGRESS_FILE -autosave 60 -t 8 \\"
            echo "            -o $OUTPUT_FILE '${new_prefix}*${current_suffix}'"
        else
            # Увеличиваем суффикс (добавляем символ в начало суффикса)
            local suffix_pos=$((${#target} - ${#current_suffix} - 1))
            local new_suffix_char="${target:$suffix_pos:1}"
            local new_suffix="${new_suffix_char}${current_suffix}"
            echo "2. Увеличить суффикс: ${current_prefix}*${new_suffix}"
            echo "   Команда: ./VanitySearch -seg $SEGMENTS_FILE -bits $BITS -kangaroo \\"
            echo "            -progress $PROGRESS_FILE -autosave 60 -t 8 \\"
            echo "            -o $OUTPUT_FILE '${current_prefix}*${new_suffix}'"
        fi
    else
        echo "🎉 Целевой адрес найден!"
    fi
    
    echo "----------------------------------------"
}

# Основной цикл поиска
run_search() {
    local pattern="${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
    
    echo "🔍 Запуск поиска: $pattern"
    echo "⏱️  Время: ${SEARCH_TIME} секунд"
    echo
    
    # Очистить предыдущие результаты
    > "$OUTPUT_FILE"
    
    # Запустить поиск с таймаутом
    timeout ${SEARCH_TIME}s ./VanitySearch \
        -seg "$SEGMENTS_FILE" \
        -bits $BITS \
        -kangaroo \
        -progress "$PROGRESS_FILE" \
        -autosave 60 \
        -t 8 \
        -o "$OUTPUT_FILE" \
        "$pattern" 2>&1 | tee incremental_search.log
    
    local exit_code=${PIPESTATUS[0]}
    
    echo
    echo "=========================================="
    
    if [ $exit_code -eq 124 ]; then
        echo "⏱️  Поиск завершен по таймауту (${SEARCH_TIME} сек)"
    elif [ $exit_code -eq 0 ]; then
        echo "✅ Поиск завершен успешно"
    else
        echo "⚠️  Поиск завершен с кодом: $exit_code"
    fi
    
    # Анализ результатов
    analyze_results "$OUTPUT_FILE" "$TARGET"
    local best_score=$?
    
    # Предложить следующий шаг
    suggest_next_step $best_score "$CURRENT_PREFIX" "$CURRENT_SUFFIX" "$TARGET"
    
    return 0
}

# Запуск
run_search

