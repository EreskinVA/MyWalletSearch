#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умный генератор сегментов для VanitySearch

Особенности:
- Генерация по процентам от диапазона (например 67.5-68.9% для 71-bit)
- Неравномерное распределение с зеркалированием
- Разнонаправленные сегменты (up/down)
- Приоритеты для оптимального распределения ресурсов
- Стратегии: центр+края, случайные, golden ratio
"""

from __future__ import annotations

import random
import argparse
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class SegmentConfig:
    """Конфигурация одного сегмента"""
    start: int
    end: int
    direction: str  # 'up' or 'down'
    name: str
    priority: int
    
    def to_line(self, mode: str = "key") -> str:
        """Конвертирует в строку формата VanitySearch"""
        if mode == "key":
            return f"key 0x{self.start:X} 0x{self.end:X} {self.direction} {self.name} {self.priority}"
        else:
            return f"abs {self.start} {self.end} {self.direction} {self.name} {self.priority}"


class SmartSegmentGenerator:
    """Генератор умных сегментов"""
    
    def __init__(self, bits: int = 71):
        self.bits = bits
        self.range_start = 2 ** (bits - 1)
        self.range_end = 2 ** bits - 1
        self.range_size = self.range_end - self.range_start + 1
        
    def percent_to_value(self, percent: float) -> int:
        """Конвертирует процент в абсолютное значение"""
        return self.range_start + int(self.range_size * (percent / 100.0))
    
    def generate_segments(
        self,
        start_percent: float,
        end_percent: float,
        segments_per_group: int,
        num_groups: int,
        strategy: str = "smart_mixed",
        min_segment_size: int = 1000000  # Минимальный размер сегмента
    ) -> List[List[SegmentConfig]]:
        """
        Генерирует группы сегментов
        
        Args:
            start_percent: Начальный процент (например 67.5)
            end_percent: Конечный процент (например 68.9)
            segments_per_group: Количество сегментов в группе
            num_groups: Количество групп
            strategy: Стратегия генерации
            min_segment_size: Минимальный размер сегмента
            
        Returns:
            Список групп сегментов
        """
        # Вычисляем абсолютные границы
        abs_start = self.percent_to_value(start_percent)
        abs_end = self.percent_to_value(end_percent)
        target_range = abs_end - abs_start
        
        if target_range < min_segment_size * segments_per_group:
            print(f"⚠️  ПРЕДУПРЕЖДЕНИЕ: Диапазон {target_range:,} слишком мал для {segments_per_group} сегментов")
            print(f"    Рекомендуется увеличить диапазон или уменьшить количество сегментов")
        
        # Выбираем стратегию
        if strategy == "smart_mixed":
            return self._strategy_smart_mixed(abs_start, abs_end, segments_per_group, num_groups, min_segment_size)
        elif strategy == "golden_ratio":
            return self._strategy_golden_ratio(abs_start, abs_end, segments_per_group, num_groups, min_segment_size)
        elif strategy == "center_heavy":
            return self._strategy_center_heavy(abs_start, abs_end, segments_per_group, num_groups, min_segment_size)
        elif strategy == "edges_focus":
            return self._strategy_edges_focus(abs_start, abs_end, segments_per_group, num_groups, min_segment_size)
        elif strategy == "random_scatter":
            return self._strategy_random_scatter(abs_start, abs_end, segments_per_group, num_groups, min_segment_size)
        else:
            raise ValueError(f"Неизвестная стратегия: {strategy}")
    
    def _strategy_smart_mixed(
        self,
        abs_start: int,
        abs_end: int,
        segments_per_group: int,
        num_groups: int,
        min_size: int
    ) -> List[List[SegmentConfig]]:
        """
        Умная смешанная стратегия:
        - Центр (высокий приоритет, up/down)
        - Края (средний приоритет, зеркалированные)
        - Случайные точки (низкий приоритет)
        """
        groups = []
        target_range = abs_end - abs_start
        
        for group_idx in range(num_groups):
            segments = []
            segment_size = max(min_size, target_range // (segments_per_group * 2))
            
            for seg_idx in range(segments_per_group):
                # Определяем тип сегмента (циклически)
                seg_type = seg_idx % 4
                
                if seg_type == 0:
                    # Центральный сегмент (высокий приоритет)
                    center = (abs_start + abs_end) // 2
                    offset = (seg_idx // 4) * segment_size
                    start = center - segment_size // 2 + offset
                    end = start + segment_size
                    direction = "up" if seg_idx % 2 == 0 else "down"
                    priority = 9
                    name = f"grp{group_idx+1}_center_{seg_idx+1}"
                    
                elif seg_type == 1:
                    # Левый край (зеркалированный)
                    offset = (seg_idx // 4) * segment_size * 2
                    start = abs_start + offset
                    end = start + segment_size
                    direction = "up"
                    priority = 7
                    name = f"grp{group_idx+1}_left_{seg_idx+1}"
                    
                elif seg_type == 2:
                    # Правый край (зеркалированный)
                    offset = (seg_idx // 4) * segment_size * 2
                    end = abs_end - offset
                    start = end - segment_size
                    direction = "down"
                    priority = 7
                    name = f"grp{group_idx+1}_right_{seg_idx+1}"
                    
                else:
                    # Случайная точка
                    random_center = random.randint(abs_start + segment_size, abs_end - segment_size)
                    start = random_center - segment_size // 2
                    end = start + segment_size
                    direction = "up" if random.random() > 0.5 else "down"
                    priority = 5
                    name = f"grp{group_idx+1}_rand_{seg_idx+1}"
                
                # Проверяем границы
                start = max(abs_start, min(start, abs_end - min_size))
                end = max(start + min_size, min(end, abs_end))
                
                segments.append(SegmentConfig(start, end, direction, name, priority))
            
            groups.append(segments)
        
        return groups
    
    def _strategy_golden_ratio(
        self,
        abs_start: int,
        abs_end: int,
        segments_per_group: int,
        num_groups: int,
        min_size: int
    ) -> List[List[SegmentConfig]]:
        """
        Стратегия золотого сечения:
        - Распределение по золотому сечению (0.618)
        - Зеркалированные пары
        - Переменные приоритеты
        """
        PHI = 0.618033988749
        groups = []
        target_range = abs_end - abs_start
        segment_size = max(min_size, target_range // (segments_per_group * 3))
        
        for group_idx in range(num_groups):
            segments = []
            
            for seg_idx in range(segments_per_group):
                # Золотое сечение
                ratio = (seg_idx + 1) / segments_per_group
                phi_ratio = (ratio * PHI) % 1.0
                
                center = abs_start + int(target_range * phi_ratio)
                start = center - segment_size // 2
                end = start + segment_size
                
                # Чередуем направление
                direction = "up" if seg_idx % 2 == 0 else "down"
                
                # Приоритет убывает от центра
                center_dist = abs(phi_ratio - 0.5)
                priority = 9 - int(center_dist * 8)
                
                name = f"grp{group_idx+1}_phi_{seg_idx+1}"
                
                # Проверяем границы
                start = max(abs_start, min(start, abs_end - min_size))
                end = max(start + min_size, min(end, abs_end))
                
                segments.append(SegmentConfig(start, end, direction, name, priority))
            
            groups.append(segments)
        
        return groups
    
    def _strategy_center_heavy(
        self,
        abs_start: int,
        abs_end: int,
        segments_per_group: int,
        num_groups: int,
        min_size: int
    ) -> List[List[SegmentConfig]]:
        """
        Стратегия с акцентом на центр:
        - 60% сегментов вокруг центра
        - 40% на краях
        - Высокие приоритеты в центре
        """
        groups = []
        target_range = abs_end - abs_start
        center = (abs_start + abs_end) // 2
        
        central_segs = int(segments_per_group * 0.6)
        edge_segs = segments_per_group - central_segs
        
        for group_idx in range(num_groups):
            segments = []
            
            # Центральные сегменты (плотно упакованные)
            central_range = target_range // 3
            central_seg_size = max(min_size, central_range // central_segs)
            
            for i in range(central_segs):
                offset = (i - central_segs // 2) * central_seg_size
                start = center + offset - central_seg_size // 2
                end = start + central_seg_size
                direction = "up" if i % 2 == 0 else "down"
                priority = 9
                name = f"grp{group_idx+1}_core_{i+1}"
                
                start = max(abs_start, min(start, abs_end - min_size))
                end = max(start + min_size, min(end, abs_end))
                
                segments.append(SegmentConfig(start, end, direction, name, priority))
            
            # Краевые сегменты
            edge_seg_size = max(min_size, target_range // (edge_segs * 2))
            
            for i in range(edge_segs):
                if i % 2 == 0:
                    # Левый край
                    start = abs_start + (i // 2) * edge_seg_size * 3
                    end = start + edge_seg_size
                    direction = "up"
                    name = f"grp{group_idx+1}_edge_left_{i+1}"
                else:
                    # Правый край
                    end = abs_end - (i // 2) * edge_seg_size * 3
                    start = end - edge_seg_size
                    direction = "down"
                    name = f"grp{group_idx+1}_edge_right_{i+1}"
                
                priority = 6
                
                start = max(abs_start, min(start, abs_end - min_size))
                end = max(start + min_size, min(end, abs_end))
                
                segments.append(SegmentConfig(start, end, direction, name, priority))
            
            groups.append(segments)
        
        return groups
    
    def _strategy_edges_focus(
        self,
        abs_start: int,
        abs_end: int,
        segments_per_group: int,
        num_groups: int,
        min_size: int
    ) -> List[List[SegmentConfig]]:
        """
        Стратегия с акцентом на края:
        - Высокая плотность на краях диапазона
        - Зеркалированные пары
        - Редкие проверки в центре
        """
        groups = []
        target_range = abs_end - abs_start
        
        edge_segs = int(segments_per_group * 0.7)
        center_segs = segments_per_group - edge_segs
        
        for group_idx in range(num_groups):
            segments = []
            
            # Краевые сегменты (половина слева, половина справа)
            edge_seg_size = max(min_size, target_range // (edge_segs * 4))
            
            for i in range(edge_segs):
                if i < edge_segs // 2:
                    # Левый край (плотно)
                    start = abs_start + i * edge_seg_size
                    end = start + edge_seg_size
                    direction = "up"
                    priority = 8
                    name = f"grp{group_idx+1}_left_{i+1}"
                else:
                    # Правый край (плотно)
                    idx = i - edge_segs // 2
                    end = abs_end - idx * edge_seg_size
                    start = end - edge_seg_size
                    direction = "down"
                    priority = 8
                    name = f"grp{group_idx+1}_right_{i+1}"
                
                start = max(abs_start, min(start, abs_end - min_size))
                end = max(start + min_size, min(end, abs_end))
                
                segments.append(SegmentConfig(start, end, direction, name, priority))
            
            # Центральные сегменты (разреженные)
            center = (abs_start + abs_end) // 2
            center_seg_size = max(min_size, target_range // (center_segs * 6))
            
            for i in range(center_segs):
                offset = (i - center_segs // 2) * center_seg_size * 3
                start = center + offset - center_seg_size // 2
                end = start + center_seg_size
                direction = "up" if i % 2 == 0 else "down"
                priority = 4
                name = f"grp{group_idx+1}_center_{i+1}"
                
                start = max(abs_start, min(start, abs_end - min_size))
                end = max(start + min_size, min(end, abs_end))
                
                segments.append(SegmentConfig(start, end, direction, name, priority))
            
            groups.append(segments)
        
        return groups
    
    def _strategy_random_scatter(
        self,
        abs_start: int,
        abs_end: int,
        segments_per_group: int,
        num_groups: int,
        min_size: int
    ) -> List[List[SegmentConfig]]:
        """
        Стратегия случайного разброса:
        - Равномерное случайное распределение
        - Без перекрытий
        - Случайные направления и приоритеты
        """
        groups = []
        target_range = abs_end - abs_start
        segment_size = max(min_size, target_range // (segments_per_group * 3))
        
        for group_idx in range(num_groups):
            segments = []
            used_ranges = []
            
            attempts = 0
            while len(segments) < segments_per_group and attempts < segments_per_group * 10:
                attempts += 1
                
                # Случайный центр
                center = random.randint(abs_start + segment_size, abs_end - segment_size)
                start = center - segment_size // 2
                end = start + segment_size
                
                # Проверяем перекрытия
                overlap = False
                for used_start, used_end in used_ranges:
                    if not (end < used_start or start > used_end):
                        overlap = True
                        break
                
                if overlap:
                    continue
                
                # Случайные параметры
                direction = "up" if random.random() > 0.5 else "down"
                priority = random.randint(5, 9)
                name = f"grp{group_idx+1}_rnd_{len(segments)+1}"
                
                # Проверяем границы
                start = max(abs_start, min(start, abs_end - min_size))
                end = max(start + min_size, min(end, abs_end))
                
                segments.append(SegmentConfig(start, end, direction, name, priority))
                used_ranges.append((start, end))
            
            if len(segments) < segments_per_group:
                print(f"⚠️  Группа {group_idx+1}: создано только {len(segments)} из {segments_per_group} сегментов (нет места)")
            
            groups.append(segments)
        
        return groups
    
    def format_segments(self, groups: List[List[SegmentConfig]], mode: str = "key") -> str:
        """Форматирует группы сегментов в текст для VanitySearch"""
        lines = []
        
        for group_idx, segments in enumerate(groups):
            if group_idx > 0:
                lines.append("")  # Пустая строка между группами
            
            lines.append(f"# Группа {group_idx + 1} ({len(segments)} сегментов)")
            
            for seg in segments:
                lines.append(seg.to_line(mode))
        
        return "\n".join(lines)
    
    def print_statistics(self, groups: List[List[SegmentConfig]]):
        """Выводит статистику по сгенерированным сегментам"""
        total_segments = sum(len(g) for g in groups)
        total_keys = 0
        directions_up = 0
        directions_down = 0
        priorities = {i: 0 for i in range(1, 10)}
        
        for group in groups:
            for seg in group:
                total_keys += seg.end - seg.start + 1
                if seg.direction == "up":
                    directions_up += 1
                else:
                    directions_down += 1
                priorities[seg.priority] = priorities.get(seg.priority, 0) + 1
        
        print(f"\n📊 СТАТИСТИКА СГЕНЕРИРОВАННЫХ СЕГМЕНТОВ:")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  Групп:         {len(groups)}")
        print(f"  Всего сегментов: {total_segments}")
        print(f"  Направлений UP:   {directions_up} ({directions_up/total_segments*100:.1f}%)")
        print(f"  Направлений DOWN: {directions_down} ({directions_down/total_segments*100:.1f}%)")
        print(f"  Общий размер:  {total_keys:,} ключей")
        print(f"  Средний размер: {total_keys//total_segments:,} ключей/сегмент")
        print(f"\n  Приоритеты:")
        for pri in sorted(priorities.keys(), reverse=True):
            if priorities[pri] > 0:
                print(f"    {pri}: {priorities[pri]:3d} сегментов ({priorities[pri]/total_segments*100:.1f}%)")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def main():
    parser = argparse.ArgumentParser(description="Умный генератор сегментов для VanitySearch")
    parser.add_argument("--bits", type=int, default=71, help="Битность пазла (default: 71)")
    parser.add_argument("--start-percent", type=float, required=True, help="Начальный процент (например 67.5)")
    parser.add_argument("--end-percent", type=float, required=True, help="Конечный процент (например 68.9)")
    parser.add_argument("--segments-per-group", type=int, required=True, help="Количество сегментов в группе")
    parser.add_argument("--num-groups", type=int, required=True, help="Количество групп")
    parser.add_argument("--strategy", type=str, default="smart_mixed",
                        choices=["smart_mixed", "golden_ratio", "center_heavy", "edges_focus", "random_scatter"],
                        help="Стратегия генерации")
    parser.add_argument("--min-size", type=int, default=1000000, help="Минимальный размер сегмента")
    parser.add_argument("--output", type=str, help="Выходной файл (если не указан - вывод в stdout)")
    parser.add_argument("--mode", type=str, default="key", choices=["key", "abs"], help="Формат вывода (key или abs)")
    parser.add_argument("--seed", type=int, help="Seed для random (для воспроизводимости)")
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
    
    # Создаем генератор
    gen = SmartSegmentGenerator(bits=args.bits)
    
    # Генерируем сегменты
    print(f"\n🎯 ГЕНЕРАЦИЯ СЕГМЕНТОВ:")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Пазл:          {args.bits} бит")
    print(f"  Диапазон:      {args.start_percent:.2f}% - {args.end_percent:.2f}%")
    print(f"  Стратегия:     {args.strategy}")
    print(f"  Сегментов/группу: {args.segments_per_group}")
    print(f"  Групп:         {args.num_groups}")
    print(f"  Мин. размер:   {args.min_size:,}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    groups = gen.generate_segments(
        start_percent=args.start_percent,
        end_percent=args.end_percent,
        segments_per_group=args.segments_per_group,
        num_groups=args.num_groups,
        strategy=args.strategy,
        min_segment_size=args.min_size
    )
    
    # Форматируем вывод
    output_text = gen.format_segments(groups, mode=args.mode)
    
    # Статистика
    gen.print_statistics(groups)
    
    # Сохраняем или выводим
    if args.output:
        output_file = Path(args.output)
        output_file.write_text(output_text, encoding="utf-8")
        print(f"✅ Сегменты сохранены в: {output_file}")
    else:
        print("📄 СГЕНЕРИРОВАННЫЕ СЕГМЕНТЫ:")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(output_text)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()

