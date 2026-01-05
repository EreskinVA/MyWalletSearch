#!/bin/bash
# Остановить все запущенные поиски VanitySearch

echo "=== Остановка всех поисков VanitySearch ==="
echo ""

# Найти все процессы
PROCS=$(pgrep -fl "VanitySearch.*-seg" || true)

if [ -z "$PROCS" ]; then
    echo "Нет запущенных процессов поиска"
else
    echo "Найденные процессы:"
    echo "$PROCS"
    echo ""
    echo "Останавливаем..."
    pkill -f "VanitySearch.*-seg" || true
    sleep 2
    
    echo ""
    echo "Проверка оставшихся процессов:"
    REMAINING=$(pgrep -fl VanitySearch || true)
    if [ -z "$REMAINING" ]; then
        echo "✓ Все процессы остановлены"
    else
        echo "⚠ Остались процессы:"
        echo "$REMAINING"
    fi
fi

