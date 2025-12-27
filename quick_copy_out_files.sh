#!/bin/bash
# Быстрое копирование out файлов с сервера (если известна директория)
# Использование: ./quick_copy_out_files.sh [remote_directory]

SERVER="root@38.117.87.47"
PORT="44236"
REMOTE_DIR="${1:-~/VanitySearch}"  # По умолчанию ~/VanitySearch, можно указать другой путь
LOCAL_DIR="./server_results"

echo "📥 Быстрое копирование out файлов из $REMOTE_DIR"
echo ""

# Создаём локальную директорию
mkdir -p "$LOCAL_DIR"

# Копируем все out файлы одной командой
echo "Копирую файлы..."
scp -P "$PORT" "$SERVER:$REMOTE_DIR/out_*.txt" "$SERVER:$REMOTE_DIR/*.out" "$LOCAL_DIR/" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Копирование завершено!"
    echo "📁 Файлы в: $LOCAL_DIR"
    ls -lh "$LOCAL_DIR" | grep -E "out_|\.out"
else
    echo "❌ Ошибка при копировании"
    echo "💡 Попробуйте указать другую директорию:"
    echo "   ./quick_copy_out_files.sh /root/VanitySearch"
fi

