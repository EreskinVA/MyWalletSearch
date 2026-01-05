#!/usr/bin/env python3
"""
Генератор сегментов для зеркального диапазона (28-29% puzzle71).
Согласно анализу п. 4.3: если целевой ключ в 71-72%, то (n - k) в 28-29%.

Стратегия: разделить на небольшие сегменты для быстрой проверки.
"""

import sys

def split_evenly(start, end, n):
    """Разбить [start, end) на n равных интервалов."""
    if n <= 0:
        raise ValueError("n must > 0")
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
    # Диапазон puzzle71
    puzzle71_min = 2**70
    puzzle71_max = 2**71 - 1
    puzzle71_range = puzzle71_max - puzzle71_min + 1
    
    # 28-29% от диапазона (зеркальный)
    pct28_start = puzzle71_min + int(puzzle71_range * 0.28)
    pct29_end = puzzle71_min + int(puzzle71_range * 0.29)
    
    # Количество сегментов (можно сделать меньше, т.к. это быстрая проверка)
    num_segs = 8  # Небольшое количество для быстрой проверки
    
    print(f"# Зеркальный диапазон (28-29% puzzle71) для Half-point mirror", file=sys.stdout)
    print(f"# Согласно анализу: если ключ в 71-72%, то (n-k) в 28-29%", file=sys.stdout)
    print(f"# Диапазон: {pct28_start} -> {pct29_end}", file=sys.stdout)
    print(f"# Количество сегментов: {num_segs}", file=sys.stdout)
    print(f"# Формат: abs <start_dec> <end_dec> up <name> <priority>", file=sys.stdout)
    print("", file=sys.stdout)
    
    intervals = split_evenly(pct28_start, pct29_end, num_segs)
    
    for i, (seg_start, seg_end) in enumerate(intervals, start=1):
        name = f"mirror_28_29_{i}"
        print(f"abs {seg_start} {seg_end} up {name} 1", file=sys.stdout)
    
    # Оценка размера
    seg_size = (pct29_end - pct28_start) // num_segs
    total_keys = pct29_end - pct28_start
    print("", file=sys.stderr)
    print(f"# Размер сегмента: ~{seg_size}", file=sys.stderr)
    print(f"# Всего ключей: ~{total_keys}", file=sys.stderr)


if __name__ == "__main__":
    main()


