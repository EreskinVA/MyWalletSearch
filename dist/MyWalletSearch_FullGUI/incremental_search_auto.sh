#!/bin/bash
# Автоматический инкрементальный поиск с адаптивной стратегией

TARGET="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
CURRENT_PREFIX="1PWo3Je"
CURRENT_SUFFIX="zXU"
SEARCH_TIME=120  # Время поиска в секундах (2 минуты)
BITS=71
SEGMENTS_FILE="segments_puzzle71.txt"
OUTPUT_FILE="incremental_results.txt"
PROGRESS_FILE="incremental_progress.dat"
LOG_FILE="incremental_search.log"
MAX_ITERATIONS=10  # Максимальное количество итераций

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "🚀 Автоматический инкрементальный поиск"
echo "========================================${NC}"
echo "🎯 Целевой адрес: $TARGET"
echo "📋 Текущий паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
echo "⏱️  Время поиска: ${SEARCH_TIME} сек"
echo "🔄 Максимум итераций: $MAX_ITERATIONS"
echo -e "${BLUE}========================================${NC}"
echo

# Функция для анализа результатов и определения следующего шага
analyze_and_suggest() {
    local output_file="$1"
    local target="$2"
    local current_prefix="$3"
    local current_suffix="$4"
    
    if [ ! -f "$output_file" ] || [ ! -s "$output_file" ]; then
        echo -e "${YELLOW}⚠️  Файл результатов пуст${NC}"
        return 1
    fi
    
    local best_match=""
    local best_score=0
    local best_pos=0
    
    # Анализируем найденные адреса
    while IFS= read -r line; do
        if [[ $line =~ ^PubAddress:[[:space:]]+(1[A-Za-z0-9]+) ]]; then
            local found_addr="${BASH_REMATCH[1]}"
            local score=0
            
            # Считаем совпадения с начала
            for ((i=0; i<${#found_addr} && i<${#target}; i++)); do
                if [ "${found_addr:$i:1}" == "${target:$i:1}" ]; then
                    ((score++))
                else
                    break
                fi
            done
            
            # Также проверяем совпадения с конца (для суффикса)
            local suffix_score=0
            local found_len=${#found_addr}
            local target_len=${#target}
            for ((i=1; i<=found_len && i<=target_len; i++)); do
                if [ "${found_addr: -$i:1}" == "${target: -$i:1}" ]; then
                    ((suffix_score++))
                else
                    break
                fi
            done
            
            if [ $score -gt $best_score ]; then
                best_score=$score
                best_match="$found_addr"
                best_pos=0  # Совпадение с начала
            fi
            
            if [ $suffix_score -gt $best_score ]; then
                best_score=$suffix_score
                best_match="$found_addr"
                best_pos=1  # Совпадение с конца
            fi
            
            echo -e "${GREEN}  ✓${NC} $found_addr (начало: $score, конец: $suffix_score)"
        fi
    done < "$output_file"
    
    echo
    echo -e "${BLUE}----------------------------------------${NC}"
    if [ $best_score -gt 0 ]; then
        echo -e "${GREEN}✅ Лучшее совпадение: $best_match${NC}"
        echo -e "   Совпадение: ${GREEN}$best_score${NC} символов"
        echo -e "   Целевой:    $target"
        
        # Определяем следующий шаг
        if [ $best_pos -eq 0 ]; then
            # Совпадение с начала - увеличиваем префикс
            if [ $best_score -lt ${#target} ]; then
                local next_char="${target:$best_score:1}"
                local new_prefix="${target:0:$((best_score + 1))}"
                echo -e "   💡 Следующий шаг: увеличить префикс до '$new_prefix'"
                echo "$new_prefix|$current_suffix"
                return 0
            fi
        else
            # Совпадение с конца - увеличиваем суффикс
            local suffix_len=$best_score
            local new_suffix="${target: -$suffix_len:}"
            echo -e "   💡 Следующий шаг: увеличить суффикс до '*$new_suffix'"
            echo "$current_prefix|$new_suffix"
            return 0
        fi
    else
        echo -e "${RED}❌ Совпадений не найдено${NC}"
        echo -e "${YELLOW}   Рекомендация: продолжить с текущим паттерном${NC}"
        echo "$current_prefix|$current_suffix"
        return 1
    fi
    
    return 0
}

# Основной цикл
iteration=1
while [ $iteration -le $MAX_ITERATIONS ]; do
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔄 Итерация $iteration/$MAX_ITERATIONS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    
    local pattern="${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
    echo -e "${YELLOW}🔍 Поиск: $pattern${NC}"
    echo -e "${YELLOW}⏱️  Время: ${SEARCH_TIME} секунд${NC}"
    echo
    
    # Очистить предыдущие результаты
    > "$OUTPUT_FILE"
    
    # Запустить поиск
    timeout ${SEARCH_TIME}s ./VanitySearch \
        -seg "$SEGMENTS_FILE" \
        -bits $BITS \
        -kangaroo \
        -progress "$PROGRESS_FILE" \
        -autosave 60 \
        -t 8 \
        -o "$OUTPUT_FILE" \
        "$pattern" > "$LOG_FILE" 2>&1
    
    local exit_code=$?
    
    echo
    if [ $exit_code -eq 124 ]; then
        echo -e "${YELLOW}⏱️  Поиск завершен по таймауту${NC}"
    elif [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Поиск завершен успешно${NC}"
    else
        echo -e "${RED}⚠️  Поиск завершен с кодом: $exit_code${NC}"
    fi
    
    # Анализ результатов
    echo
    echo -e "${BLUE}📊 Анализ результатов:${NC}"
    result=$(analyze_and_suggest "$OUTPUT_FILE" "$TARGET" "$CURRENT_PREFIX" "$CURRENT_SUFFIX")
    
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        IFS='|' read -r new_prefix new_suffix <<< "$result"
        
        if [ "$new_prefix" != "$CURRENT_PREFIX" ] || [ "$new_suffix" != "$CURRENT_SUFFIX" ]; then
            echo
            echo -e "${GREEN}📈 Обновление паттерна:${NC}"
            echo -e "   Было: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
            echo -e "   Стало: ${new_prefix}*${new_suffix}"
            CURRENT_PREFIX="$new_prefix"
            CURRENT_SUFFIX="$new_suffix"
        fi
    fi
    
    # Проверка на достижение цели
    local target_len=${#TARGET}
    local prefix_len=${#CURRENT_PREFIX}
    local suffix_len=${#CURRENT_SUFFIX}
    local total_len=$((prefix_len + suffix_len))
    
    if [ $total_len -ge $target_len ]; then
        echo
        echo -e "${GREEN}🎉 Паттерн покрывает весь целевой адрес!${NC}"
        echo -e "   Можно перейти к финальному поиску"
        break
    fi
    
    echo
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    
    ((iteration++))
    
    # Небольшая пауза между итерациями
    sleep 2
done

echo
echo -e "${BLUE}=========================================="
echo "📋 Итоговый отчет"
echo "========================================${NC}"
echo "🎯 Целевой адрес: $TARGET"
echo "📋 Финальный паттерн: ${CURRENT_PREFIX}*${CURRENT_SUFFIX}"
echo "📁 Результаты сохранены в: $OUTPUT_FILE"
echo "📝 Лог сохранен в: $LOG_FILE"
echo -e "${BLUE}========================================${NC}"

