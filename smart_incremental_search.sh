#!/bin/bash
# Умный инкрементальный поиск с автоматическим анализом и перестройкой сегментов

TARGET="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
CURRENT_PREFIX="1PW"
CURRENT_SUFFIX="U"
SEARCH_TIME=60  # Время поиска в секундах
BITS=71
BASE_SEGMENTS_FILE="segments_puzzle71.txt"
FOCUSED_SEGMENTS_FILE="segments_focused.txt"
OUTPUT_FILE="smart_search_results.txt"
PROGRESS_FILE="smart_search_progress.dat"
LOG_FILE="smart_search.log"
ITERATION=1
MAX_ITERATIONS=15

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "🧠 Умный инкрементальный поиск"
echo "========================================${NC}"
echo "🎯 Целевой адрес: $TARGET"
echo "📋 Начальный паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
echo "⏱️  Время поиска: ${SEARCH_TIME} сек"
echo "🔄 Максимум итераций: $MAX_ITERATIONS"
echo -e "${BLUE}========================================${NC}"
echo

# Функция для анализа результатов и определения следующего паттерна
analyze_and_refine() {
    local output_file="$1"
    local target="$2"
    
    if [ ! -f "$output_file" ] || [ ! -s "$output_file" ]; then
        echo -e "${YELLOW}⚠️  Файл результатов пуст${NC}" >&2
        return 1
    fi
    
    echo -e "${CYAN}📊 Анализ результатов...${NC}" >&2
    
    # Использовать Python скрипт для анализа (вывод в stderr)
    python3 analyze_and_refine.py "$output_file" "$target" $BITS >&2
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Ошибка при анализе${NC}" >&2
        return 1
    fi
    
    # Найти лучшее совпадение для определения следующего паттерна
    local best_score=0
    local best_addr=""
    
    while IFS= read -r line; do
        if [[ $line =~ ^PubAddress:[[:space:]]+(1[A-Za-z0-9]+) ]]; then
            local found_addr="${BASH_REMATCH[1]}"
            local score=0
            
            for ((i=0; i<${#found_addr} && i<${#target}; i++)); do
                if [ "${found_addr:$i:1}" == "${target:$i:1}" ]; then
                    ((score++))
                else
                    break
                fi
            done
            
            if [ $score -gt $best_score ]; then
                best_score=$score
                best_addr="$found_addr"
            fi
        fi
    done < "$output_file"
    
    if [ $best_score -gt 0 ]; then
        echo -e "${GREEN}✅ Лучшее совпадение: $best_addr ($best_score символов)${NC}" >&2
        
        # Определить следующий паттерн
        if [ $best_score -lt ${#target} ]; then
            local next_char="${target:$best_score:1}"
            local new_prefix="${target:0:$((best_score + 1))}"
            
            # Определить, увеличивать префикс или суффикс
            local prefix_end=$((${#target} - ${#CURRENT_SUFFIX}))
            
            if [ $best_score -lt $prefix_end ]; then
                # Увеличиваем префикс
                echo -e "${CYAN}💡 Следующий паттерн: ${new_prefix}*${CURRENT_SUFFIX}${NC}" >&2
                echo "${new_prefix}|${CURRENT_SUFFIX}"
                return 0
            else
                # Увеличиваем суффикс
                local suffix_len=$((${#target} - $best_score))
                local new_suffix="${target: -$suffix_len:}"
                echo -e "${CYAN}💡 Следующий паттерн: ${CURRENT_PREFIX}*${new_suffix}${NC}" >&2
                echo "${CURRENT_PREFIX}|${new_suffix}"
                return 0
            fi
        fi
    fi
    
    return 1
}

# Основной цикл
while [ $ITERATION -le $MAX_ITERATIONS ]; do
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔄 Итерация $ITERATION/$MAX_ITERATIONS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    
    pattern="${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
    echo -e "${YELLOW}🔍 Поиск: $pattern${NC}"
    echo -e "${YELLOW}⏱️  Время: ${SEARCH_TIME} секунд${NC}"
    
    # Определить, какой файл сегментов использовать
    segments_file="$BASE_SEGMENTS_FILE"
    if [ -f "$FOCUSED_SEGMENTS_FILE" ] && [ $ITERATION -gt 1 ]; then
        segments_file="$FOCUSED_SEGMENTS_FILE"
        echo -e "${CYAN}📁 Используются сфокусированные сегменты${NC}"
    fi
    
    echo
    
    # Очистить предыдущие результаты
    > "$OUTPUT_FILE"
    
    # Запустить поиск
    timeout ${SEARCH_TIME}s ./VanitySearch \
        -seg "$segments_file" \
        -bits $BITS \
        -kangaroo \
        -progress "$PROGRESS_FILE" \
        -autosave 30 \
        -t 4 \
        -o "$OUTPUT_FILE" \
        "$pattern" > "$LOG_FILE" 2>&1
    
    exit_code=$?
    
    echo
    if [ $exit_code -eq 124 ]; then
        echo -e "${YELLOW}⏱️  Поиск завершен по таймауту${NC}"
    elif [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Поиск завершен успешно${NC}"
    else
        echo -e "${RED}⚠️  Поиск завершен с кодом: $exit_code${NC}"
    fi
    
    # Проверить, найдены ли адреса
    found_count=$(grep -c "^PubAddress:" "$OUTPUT_FILE" 2>/dev/null || echo "0")
    
    if [ "$found_count" -gt 0 ]; then
        echo -e "${GREEN}✅ Найдено адресов: $found_count${NC}"
        
        # Анализ и перестройка сегментов
        echo
        result=$(analyze_and_refine "$OUTPUT_FILE" "$TARGET")
        
        if [ $? -eq 0 ] && [ -n "$result" ]; then
            IFS='|' read -r new_prefix new_suffix <<< "$result"
            
            if [ "$new_prefix" != "$CURRENT_PREFIX" ] || [ "$new_suffix" != "$CURRENT_SUFFIX" ]; then
                echo
                echo -e "${GREEN}📈 Обновление паттерна:${NC}"
                echo -e "   Было: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
                echo -e "   Стало: ${new_prefix}*${new_suffix}"
                CURRENT_PREFIX="$new_prefix"
                CURRENT_SUFFIX="$new_suffix"
                
                # Если создан файл сфокусированных сегментов, использовать его в следующей итерации
                if [ -f "$FOCUSED_SEGMENTS_FILE" ]; then
                    echo -e "${CYAN}📁 Сфокусированные сегменты готовы для следующей итерации${NC}"
                fi
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  Адреса не найдены${NC}"
        echo -e "${YELLOW}   Продолжаем с текущим паттерном${NC}"
    fi
    
    # Проверка на достижение цели
    target_len=${#TARGET}
    prefix_len=${#CURRENT_PREFIX}
    suffix_len=${#CURRENT_SUFFIX}
    total_len=$((prefix_len + suffix_len))
    
    if [ $total_len -ge $target_len ]; then
        echo
        echo -e "${GREEN}🎉 Паттерн покрывает весь целевой адрес!${NC}"
        break
    fi
    
    echo
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    
    ((ITERATION++))
    sleep 2
done

echo
echo -e "${BLUE}=========================================="
echo "📋 Итоговый отчет"
echo "========================================${NC}"
echo "🎯 Целевой адрес: $TARGET"
echo "📋 Финальный паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
echo "📁 Результаты: $OUTPUT_FILE"
echo "📝 Лог: $LOG_FILE"
if [ -f "$FOCUSED_SEGMENTS_FILE" ]; then
    echo "📁 Сфокусированные сегменты: $FOCUSED_SEGMENTS_FILE"
fi
echo -e "${BLUE}========================================${NC}"

