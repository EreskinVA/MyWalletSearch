#!/usr/bin/env python3
"""
Генератор широких ABS-сегментов для GPU на сервере.
Паттерн: 1PWo3JeB (8 символов) - GPU-фаза согласно анализу.

Диапазон: ~2.026×10^21 … ~2.038×10^21 (широкий, покрывает 71.5-72.5% + запас)
Количество сегментов: 32 (оптимально для GPU)
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
    # Широкий диапазон (с запасом от найденных ключей)
    start = 2026000000000000000000
    end = 2038000000000000000000
    
    # 32 сегмента для GPU
    num_segs = 32
    
    print(f"# GPU широкий поиск: паттерн 1PWo3JeB (8 символов)", file=sys.stdout)
    print(f"# Диапазон: {start} -> {end}", file=sys.stdout)
    print(f"# Количество сегментов: {num_segs}", file=sys.stdout)
    print(f"# Формат: abs <start_dec> <end_dec> up <name> <priority>", file=sys.stdout)
    print("", file=sys.stdout)
    
    intervals = split_evenly(start, end, num_segs)
    
    for i, (seg_start, seg_end) in enumerate(intervals, start=1):
        name = f"gpu_b9_wide_{i}"
        print(f"abs {seg_start} {seg_end} up {name} 1", file=sys.stdout)


if __name__ == "__main__":
    main()

