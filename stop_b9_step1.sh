#!/bin/bash
# Остановка всех экземпляров Step 1

echo "Остановка Step 1 поиска..."

pkill -f 'VanitySearch.*-seg.*seg_b9_step1' || echo "Процессы не найдены"

sleep 1

# Проверка что всё остановлено
if pgrep -f 'VanitySearch.*-seg.*seg_b9_step1' > /dev/null; then
    echo "⚠ Некоторые процессы всё ещё работают, принудительная остановка..."
    pkill -9 -f 'VanitySearch.*-seg.*seg_b9_step1'
else
    echo "✓ Все процессы остановлены"
fi

