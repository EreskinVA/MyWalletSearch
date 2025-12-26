#!/bin/bash
# Скрипт остановки VanitySearch (работает без pkill)

echo "🔍 Ищу процессы VanitySearch..."
echo ""

PIDS=$(ps aux | grep '[V]anitySearch' | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "✅ Процессы VanitySearch не найдены"
    exit 0
fi

echo "Найдены процессы:"
ps aux | grep '[V]anitySearch' | grep -v grep
echo ""

# Попытка мягкой остановки
echo "⏸️  Останавливаю процессы (мягкая остановка)..."
echo "$PIDS" | xargs -r kill

sleep 2

# Проверка
REMAINING=$(ps aux | grep '[V]anitySearch' | grep -v grep | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Все процессы успешно остановлены"
    exit 0
fi

# Если остались - форсированная остановка
echo "⚠️  Некоторые процессы не остановились. Форсированная остановка..."
ps aux | grep '[V]anitySearch' | awk '{print $2}' | xargs -r kill -9

sleep 1

# Финальная проверка
REMAINING=$(ps aux | grep '[V]anitySearch' | grep -v grep | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Все процессы остановлены (форсированно)"
else
    echo "❌ Ошибка: Не удалось остановить все процессы"
    echo "Оставшиеся процессы:"
    ps aux | grep '[V]anitySearch' | grep -v grep
    exit 1
fi

