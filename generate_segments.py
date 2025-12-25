#!/usr/bin/env python3
"""
Генерация файлов сегментов (4 процесса × 8 сегментов) по абсолютному decimal-диапазону.

Важно: деление делаем только целочисленное. Если размер части/сегмента не делится нацело,
остаток распределяем по первым сегментам (чтобы не было «огромного» последнего сегмента).
"""

from __future__ import annotations


START = 2128350382728406075874
END = 2128351282728406075898  # верхняя граница (включительно/исключительно зависит от реализации; здесь используем как конец диапазона)

PARTS = 4
SEGS_PER_PART = 8


def split_evenly(start: int, end: int, n: int) -> list[tuple[int, int]]:
    """Возвращает n подряд идущих интервалов [a,b) (последний заканчивается ровно в end)."""
    if n <= 0:
        raise ValueError("n must be > 0")
    if end < start:
        raise ValueError("end must be >= start")

    total = end - start
    base = total // n
    rem = total % n

    out: list[tuple[int, int]] = []
    cur = start
    for i in range(n):
        step = base + (1 if i < rem else 0)
        nxt = cur + step
        if i == n - 1:
            nxt = end
        out.append((cur, nxt))
        cur = nxt
    return out


def main() -> None:
    total = END - START
    print(f"Общий диапазон: {START} -> {END}")
    print(f"Размер диапазона: {total:,}")
    print(f"Частей: {PARTS}, сегментов в части: {SEGS_PER_PART}")
    print()

    parts = split_evenly(START, END, PARTS)
    for part_idx, (p_start, p_end) in enumerate(parts, start=1):
        segs = split_evenly(p_start, p_end, SEGS_PER_PART)
        filename = f"seg_part{part_idx}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Часть {part_idx}: {p_start} -> {p_end}\n")
            f.write(f"# Размер части: {(p_end - p_start):,}\n")
            f.write("# Формат: abs <start_dec> <end_dec> <up|down> <name> [priority]\n")
            f.write("# Примечание: интервалы генерируются подряд без разрывов и перекрытий.\n\n")
            for seg_idx, (s_start, s_end) in enumerate(segs, start=1):
                seg_name = f"seg{part_idx}_{seg_idx}"
                f.write(f"abs {s_start} {s_end} up {seg_name} 1\n")

        print(f"Создан {filename}: {p_start} -> {p_end} (size={(p_end - p_start):,})")

    print("\nГотово!")


if __name__ == "__main__":
    main()

