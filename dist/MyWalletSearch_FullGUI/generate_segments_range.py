#!/usr/bin/env python3
"""
Генератор ABS-сегментов для SegmentSearch.

Пример (ваш GPU диапазон, 4×8=32 сегмента в одном файле):
  python3 generate_segments_range.py \
    --start 2128351282728406045898 \
    --end   2128355282728406010719 \
    --parts 4 --segs-per-part 8 \
    --out seg_gpu_range.txt \
    --name-prefix gpu \
    --direction up \
    --priority 1
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    start: int
    end: int


def split_evenly(start: int, end: int, n: int) -> list[Interval]:
    """Разбить [start, end) на n подряд идущих интервалов без разрывов/перекрытий."""
    if n <= 0:
        raise ValueError("n must be > 0")
    if end < start:
        raise ValueError("end must be >= start")
    total = end - start
    base = total // n
    rem = total % n
    out: list[Interval] = []
    cur = start
    for i in range(n):
        step = base + (1 if i < rem else 0)
        nxt = cur + step
        if i == n - 1:
            nxt = end
        out.append(Interval(cur, nxt))
        cur = nxt
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, required=True, help="Начало диапазона (decimal)")
    ap.add_argument("--end", type=int, required=True, help="Конец диапазона (decimal)")
    ap.add_argument("--parts", type=int, default=4, help="Сколько крупных частей")
    ap.add_argument("--segs-per-part", type=int, default=8, help="Сколько сегментов в каждой части")
    ap.add_argument("--out", type=str, required=True, help="Имя выходного seg-файла")
    ap.add_argument("--direction", choices=["up", "down"], default="up")
    ap.add_argument("--priority", type=int, default=1)
    ap.add_argument("--name-prefix", type=str, default="seg")
    args = ap.parse_args()

    start = args.start
    end = args.end
    parts_n = args.parts
    segs_n = args.segs_per_part
    direction = args.direction
    prio = args.priority if args.priority > 0 else 1

    total = end - start
    parts = split_evenly(start, end, parts_n)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# ABS диапазон (decimal): {start} -> {end}\n")
        f.write(f"# Размер диапазона: {total}\n")
        f.write(f"# Разбиение: parts={parts_n}, segs_per_part={segs_n} (итого {parts_n * segs_n})\n")
        f.write("# Формат: abs <start_dec> <end_dec> <up|down> <name> [priority]\n\n")

        seg_global = 0
        for p_idx, part in enumerate(parts, start=1):
            segs = split_evenly(part.start, part.end, segs_n)
            f.write(f"# Part {p_idx}: {part.start} -> {part.end} (size={part.end - part.start})\n")
            for s_idx, seg in enumerate(segs, start=1):
                seg_global += 1
                name = f"{args.name_prefix}{p_idx}_{s_idx}"
                f.write(f"abs {seg.start} {seg.end} {direction} {name} {prio}\n")
            f.write("\n")

    print(f"OK: {args.out}")
    print(f"range: {start} -> {end} (size={total})")
    print(f"segments: {parts_n * segs_n}")


if __name__ == "__main__":
    main()


