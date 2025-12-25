#!/bin/bash
# Подсчёт найденных кошельков для Step 1 (оба экземпляра)

PART1="out_b9_step1_part1.txt"
PART2="out_b9_step1_part2.txt"

TOTAL=0

if [ -f "$PART1" ]; then
    COUNT1=$(wc -l < "$PART1" | tr -d ' ')
    echo "Part 1: $COUNT1 найденных"
    TOTAL=$((TOTAL + COUNT1))
else
    echo "Part 1: файл не найден"
fi

if [ -f "$PART2" ]; then
    COUNT2=$(wc -l < "$PART2" | tr -d ' ')
    echo "Part 2: $COUNT2 найденных"
    TOTAL=$((TOTAL + COUNT2))
else
    echo "Part 2: файл не найден"
fi

echo "---"
echo "Всего: $TOTAL найденных кошельков"

