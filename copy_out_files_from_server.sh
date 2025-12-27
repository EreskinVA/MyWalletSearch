#!/bin/bash
# Скрипт для копирования всех out файлов с сервера
# Использование: ./copy_out_files_from_server.sh

SERVER="root@38.117.87.47"
PORT="44236"
REMOTE_DIR="~"  # Или укажите конкретную директорию, например: /root/VanitySearch
LOCAL_DIR="./server_results"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  📥 КОПИРОВАНИЕ OUT ФАЙЛОВ С СЕРВЕРА                                       ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Создаём локальную директорию для результатов
mkdir -p "$LOCAL_DIR"

echo "🔍 Шаг 1: Поиск всех out файлов на сервере..."
echo ""

# Находим все out файлы на сервере (с таймаутом)
OUT_FILES=$(timeout 30 ssh -o ConnectTimeout=10 -p "$PORT" "$SERVER" "find $REMOTE_DIR \( -name 'out_*.txt' -o -name 'out_*.out' -o -name '*.out' \) -type f 2>/dev/null" 2>/dev/null | grep -v "^$" | grep -v "Welcome to vast.ai" | grep -v "Have fun!")

if [ -z "$OUT_FILES" ]; then
    echo "❌ Out файлы не найдены на сервере!"
    echo ""
    echo "💡 Попробуйте указать другую директорию:"
    echo "   Измените REMOTE_DIR в скрипте или выполните вручную:"
    echo "   ssh -p $PORT $SERVER 'find /root/VanitySearch -name \"out_*.txt\" -o -name \"*.out\"'"
    exit 1
fi

FILE_COUNT=$(echo "$OUT_FILES" | wc -l | tr -d ' ')
echo "✅ Найдено файлов: $FILE_COUNT"
echo ""
echo "📋 Список найденных файлов:"
echo "$OUT_FILES" | head -20
if [ "$FILE_COUNT" -gt 20 ]; then
    echo "... и ещё $((FILE_COUNT - 20)) файлов"
fi
echo ""

echo "📥 Шаг 2: Копирование файлов..."
echo ""

# Копируем каждый файл
COPIED=0
FAILED=0

for file in $OUT_FILES; do
    # Получаем имя файла без пути
    filename=$(basename "$file")
    
    # Пропускаем, если файл уже скопирован
    if [ -f "$LOCAL_DIR/$filename" ]; then
        echo "   ⏭️  Пропущен (уже существует): $filename"
        continue
    fi
    
    echo -n "   Копирую: $filename ... "
    
    # Копируем с таймаутом (5 минут на файл) и подавляем вывод приветствия
    if timeout 300 scp -o ConnectTimeout=10 -P "$PORT" "$SERVER:$file" "$LOCAL_DIR/" 2>&1 | grep -v "Welcome to vast.ai" | grep -v "Have fun!" > /dev/null 2>&1; then
        echo "✅"
        ((COPIED++))
    else
        # Проверяем, действительно ли файл не скопировался
        if [ -f "$LOCAL_DIR/$filename" ]; then
            echo "✅ (уже существует)"
            ((COPIED++))
        else
            echo "❌"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║  📊 РЕЗУЛЬТАТЫ                                                             ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Успешно скопировано: $COPIED"
if [ "$FAILED" -gt 0 ]; then
    echo "❌ Ошибок при копировании: $FAILED"
fi
echo ""
echo "📁 Файлы сохранены в: $LOCAL_DIR"
echo ""
echo "💡 Для просмотра скопированных файлов:"
echo "   ls -lh $LOCAL_DIR/"
echo ""

