#!/usr/bin/env python3
"""
Statistical Segment Optimizer
Автоматическое определение оптимальных сегментов на основе статистики
"""

import sys
import argparse
from typing import List, Tuple

def calculate_percentile(value: int, min_val: int, max_val: int) -> float:
    """Вычислить процентиль значения в диапазоне"""
    if max_val == min_val:
        return 50.0
    return ((value - min_val) / (max_val - min_val)) * 100.0

def generate_segments_from_predictions(predictions: List[float], 
                                       spread: float = 5.0,
                                       num_zones: int = 3) -> List[Tuple[float, float, str, str]]:
    """
    Генерировать сегменты на основе прогнозов
    
    Args:
        predictions: Список процентилей прогнозов
        spread: Ширина зоны вокруг каждого прогноза (%)
        num_zones: Количество концентрических зон
        
    Returns:
        List of (start%, end%, direction, name)
    """
    segments = []
    
    # Центральная зона (встречное движение)
    if predictions:
        center = sum(predictions) / len(predictions)
        segments.append((center - spread, center + spread, "up", "central_up"))
        segments.append((center + spread + 2, center, "down", "central_down"))
    
    # Зоны вокруг каждого прогноза
    for i, pred in enumerate(predictions):
        zone_name = f"hotspot_{int(pred)}"
        start = max(0, pred - spread/2)
        end = min(100, pred + spread/2)
        segments.append((start, end, "up", zone_name))
    
    # Концентрические зоны если нужно больше покрытия
    if num_zones > 1 and predictions:
        center = sum(predictions) / len(predictions)
        for i in range(1, num_zones):
            zone_spread = spread * (i + 1)
            start = max(0, center - zone_spread)
            end = min(100, center + zone_spread)
            segments.append((start, end, "up", f"zone_{i}"))
    
    return segments

def optimize_segments_for_puzzle(puzzle_num: int, 
                                  analysis_data: dict = None) -> List[Tuple[float, float, str, str]]:
    """
    Оптимизировать сегменты для конкретного puzzle
    
    Args:
        puzzle_num: Номер puzzle (например, 71)
        analysis_data: Данные анализа (опционально)
        
    Returns:
        List of segments (start%, end%, direction, name)
    """
    segments = []
    
    # Для Puzzle 71 используем данные из анализа
    if puzzle_num == 71:
        # Прогнозы из PUZZLE_71_ANALYSIS.md:
        # 1. Тренд-анализ: 53.24%
        # 2. Взвешенная средняя: 50.60%
        # 3. Средняя позиция: 50.15%
        predictions = [53.24, 50.60, 50.15]
        
        # Генерация сегментов
        segments = [
            # Центральная зона (встречное движение)
            (48.0, 54.0, "up", "central_up"),
            (56.0, 54.0, "down", "central_down"),
            
            # Горячие точки на основе прогнозов
            (52.0, 54.5, "up", "hotspot_53"),
            (49.5, 51.5, "up", "hotspot_50"),
            
            # Расширенный поиск
            (45.0, 48.0, "up", "extended_low"),
            (56.0, 59.0, "up", "extended_high"),
        ]
    else:
        # Для других puzzle - общий подход
        # Фокус на центральной зоне (45-55%)
        segments = [
            (45.0, 55.0, "up", "central_zone"),
            (50.0, 52.0, "up", "core_zone"),
        ]
    
    return segments

def generate_config_file(segments: List[Tuple[float, float, str, str]], 
                         output_file: str,
                         puzzle_num: int = None):
    """
    Сгенерировать конфигурационный файл сегментов
    
    Args:
        segments: Список сегментов
        output_file: Путь к выходному файлу
        puzzle_num: Номер puzzle (для комментариев)
    """
    with open(output_file, 'w') as f:
        f.write("# Автоматически сгенерированная конфигурация сегментов\n")
        if puzzle_num:
            f.write(f"# Оптимизирована для Puzzle {puzzle_num}\n")
        f.write("# Сгенерировано: statistical_optimizer.py\n")
        f.write("#\n")
        f.write("# Формат: startPercent endPercent direction [name]\n")
        f.write("#\n\n")
        
        for start, end, direction, name in segments:
            f.write(f"{start:.2f} {end:.2f} {direction:5s} {name}\n")
    
    print(f"✓ Конфигурация сохранена: {output_file}")
    print(f"  Сегментов: {len(segments)}")

def main():
    parser = argparse.ArgumentParser(
        description="Автоматическое определение оптимальных сегментов для поиска"
    )
    parser.add_argument("puzzle_num", type=int, 
                       help="Номер puzzle (например, 71)")
    parser.add_argument("-o", "--output", default="segments_optimized.txt",
                       help="Выходной файл конфигурации (default: segments_optimized.txt)")
    parser.add_argument("--spread", type=float, default=5.0,
                       help="Ширина зоны вокруг прогнозов в %% (default: 5.0)")
    parser.add_argument("--zones", type=int, default=3,
                       help="Количество концентрических зон (default: 3)")
    parser.add_argument("--verbose", action="store_true",
                       help="Подробный вывод")
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Оптимизация сегментов для Puzzle {args.puzzle_num}")
        print(f"Ширина зоны: {args.spread}%")
        print(f"Количество зон: {args.zones}")
        print()
    
    # Генерация оптимальных сегментов
    segments = optimize_segments_for_puzzle(args.puzzle_num)
    
    if args.verbose:
        print("Сгенерированные сегменты:")
        for i, (start, end, direction, name) in enumerate(segments, 1):
            print(f"  {i}. {name:20s} {start:6.2f}% -> {end:6.2f}% ({direction})")
        print()
    
    # Сохранение в файл
    generate_config_file(segments, args.output, args.puzzle_num)
    
    print()
    print("Использование:")
    print(f"  ./VanitySearch -seg {args.output} -bits {args.puzzle_num} -t 8 <prefix>")

if __name__ == "__main__":
    main()

