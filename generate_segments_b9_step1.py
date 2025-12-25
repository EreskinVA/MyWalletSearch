#!/usr/bin/env python3
"""
Генератор узких ABS-сегментов для Step 1: паттерн 1PWo3JeB9.

Согласно анализу:
- Центр: ~2.0266×10^21 (2026682282231556070880 из найденных)
- Ширина сегмента: ~6×10^15 (в 8 раз меньше текущих 4.9×10^16)
- Количество: 16 сегментов для CPU
"""

import sys

def split_evenly(start, end, n):
    """Разбить [start, end) на n равных интервалов."""
    if n <= 0:
        raise ValueError("n must be > 0")
    total = end - start
    base = total // n
    rem = total % n
    intervals = []
    cur = start
    for i in range(n):
        step = base + (1 if i < rem else 0)
        nxt = cur + step
        if i == n - 1:
            nxt = end
        intervals.append((cur, nxt))
        cur = nxt
    return intervals


def main():
    # Центр согласно анализу (примерное значение из найденных ключей)
    center = 2026682282231556070880
    
    # Ширина каждого сегмента: ~6×10^15
    seg_width = 6000000000000000
    
    # Количество сегментов для CPU
    num_segs = 16
    
    # Общий диапазон: центрируем вокруг center
    total_range = seg_width * num_segs
    start = center - total_range // 2
    end = start + total_range
    
    print(f"# Step 1: Узкие сегменты для паттерна 1PWo3JeB9", file=sys.stdout)
    print(f"# Центр: {center}", file=sys.stdout)
    print(f"# Диапазон: {start} -> {end}", file=sys.stdout)
    print(f"# Ширина сегмента: {seg_width} (~6×10^15)", file=sys.stdout)
    print(f"# Количество сегментов: {num_segs}", file=sys.stdout)
    print(f"# Формат: abs <start_dec> <end_dec> up <name> <priority>", file=sys.stdout)
    print("", file=sys.stdout)
    
    intervals = split_evenly(start, end, num_segs)
    
    for i, (seg_start, seg_end) in enumerate(intervals, start=1):
        name = f"cpu_b9_step1_{i}"
        print(f"abs {seg_start} {seg_end} up {name} 1", file=sys.stdout)


if __name__ == "__main__":
    main()

