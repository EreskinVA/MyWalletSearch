#!/bin/bash
# Подсчет найденных кошельков из всех 4 экземпляров

echo "=== Найдено кошельков ==="
total=0
for f in out_part1.txt out_part2.txt out_part3.txt out_part4.txt; do
  if [ -f "$f" ]; then
    count=$(wc -l < "$f" 2>/dev/null || echo 0)
    echo "$f: $count"
    total=$((total + count))
  else
    echo "$f: файл не найден"
  fi
done
echo "Всего: $total"

