#!/usr/bin/env python3
"""
Генератор сегментов для "соседних ключей" (±256 от найденных).

Согласно анализу п. 4.1: просканировать ±256 ключей от найденного приватного ключа
(из-за off-by-one ошибок при создании кошельков).

Использование:
  python3 generate_segments_neighbors.py out_cpu_p1.txt out_cpu_p2.txt ... > seg_neighbors.txt
"""

import sys
import re

def extract_puzzle_key_abs(filepath):
    """Извлечь PuzzleKeyAbs (DEC) из out файла."""
    keys = []
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            # Ищем строки типа: PuzzleKeyAbs (DEC): 2026682282231556070880
            pattern = r'PuzzleKeyAbs \(DEC\): (\d+)'
            matches = re.findall(pattern, content)
            for match in matches:
                key = int(match)
                keys.append(key)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Ошибка при чтении {filepath}: {e}", file=sys.stderr)
    return keys


def main():
    if len(sys.argv) < 2:
        print("Использование: python3 generate_segments_neighbors.py <out_file1> [<out_file2> ...]")
        print("Пример: python3 generate_segments_neighbors.py out_cpu_p1.txt out_cpu_p2.txt out_cpu_p3.txt")
        sys.exit(1)
    
    all_keys = []
    for filepath in sys.argv[1:]:
        keys = extract_puzzle_key_abs(filepath)
        all_keys.extend(keys)
        if keys:
            print(f"# Из {filepath}: найдено {len(keys)} ключей", file=sys.stderr)
    
    if not all_keys:
        print("Ошибка: не найдено ни одного PuzzleKeyAbs в указанных файлах", file=sys.stderr)
        sys.exit(1)
    
    # Убираем дубликаты
    unique_keys = sorted(set(all_keys))
    
    print("# Сегменты для проверки соседних ключей (±256 от найденных)", file=sys.stdout)
    print(f"# Всего уникальных ключей: {len(unique_keys)}", file=sys.stdout)
    print(f"# Диапазон проверки: ±256 ключей от каждого найденного", file=sys.stdout)
    print(f"# Формат: abs <start_dec> <end_dec> up <name> <priority>", file=sys.stdout)
    print("", file=sys.stdout)
    
    neighbor_range = 256  # ±256
    
    for i, key in enumerate(unique_keys, start=1):
        start = key - neighbor_range
        end = key + neighbor_range + 1  # +1 чтобы включить ключ key+256
        
        # Проверка что не выходим за границы puzzle71 (2^70 .. 2^71-1)
        puzzle71_min = 2**70
        puzzle71_max = 2**71 - 1
        
        if start < puzzle71_min:
            start = puzzle71_min
        if end > puzzle71_max:
            end = puzzle71_max + 1
        
        name = f"neighbor_{i}"
        print(f"abs {start} {end} up {name} 1", file=sys.stdout)
    
    print("", file=sys.stdout)
    print(f"# Всего сегментов: {len(unique_keys)}", file=sys.stderr)
    total_keys = len(unique_keys) * (neighbor_range * 2 + 1)
    print(f"# Всего ключей для проверки: ~{total_keys}", file=sys.stderr)


if __name__ == "__main__":
    main()


