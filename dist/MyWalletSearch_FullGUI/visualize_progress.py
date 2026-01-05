#!/usr/bin/env python3
"""
Progress Visualization Tool
Визуализация прогресса поиска по сегментам
"""

import sys
import argparse
import os
from typing import List, Dict, Tuple

def parse_progress_file(filename: str) -> Dict:
    """Парсинг файла прогресса"""
    progress = {
        'version': 0,
        'bitRange': 0,
        'totalKeysChecked': 0,
        'startTime': 0,
        'lastSaveTime': 0,
        'targetAddress': '',
        'segments': []
    }
    
    if not os.path.exists(filename):
        return progress
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    in_segment = False
    current_segment = {}
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if '=' in line:
            key, value = line.split('=', 1)
            
            if key == 'BitRange':
                progress['bitRange'] = int(value)
            elif key == 'TotalKeysChecked':
                progress['totalKeysChecked'] = int(value)
            elif key == 'StartTime':
                progress['startTime'] = int(value)
            elif key == 'LastSaveTime':
                progress['lastSaveTime'] = int(value)
            elif key == 'TargetAddress':
                progress['targetAddress'] = value
            elif in_segment:
                if key == 'Name':
                    current_segment['name'] = value
                elif key == 'StartPercent':
                    current_segment['startPercent'] = float(value)
                elif key == 'EndPercent':
                    current_segment['endPercent'] = float(value)
                elif key == 'Direction':
                    current_segment['direction'] = 'up' if value == '0' else 'down'
                elif key == 'Active':
                    current_segment['active'] = (value == '1')
                elif key == 'KeysChecked':
                    current_segment['keysChecked'] = int(value)
        
        if line == 'SEGMENT_START':
            in_segment = True
            current_segment = {}
        elif line == 'SEGMENT_END':
            in_segment = False
            progress['segments'].append(current_segment)
    
    return progress

def visualize_segments_ascii(segments: List[Dict], width: int = 80):
    """ASCII визуализация сегментов"""
    print("\n" + "=" * width)
    print("ВИЗУАЛИЗАЦИЯ ПРОГРЕССА ПО СЕГМЕНТАМ".center(width))
    print("=" * width + "\n")
    
    # Шкала 0-100%
    print("Шкала (0% - 100%):")
    scale = "0%"  + " " * (width-10) + "100%"
    print(scale)
    print("├" + "─" * (width-2) + "┤")
    
    # Каждый сегмент
    for seg in segments:
        start = seg.get('startPercent', 0)
        end = seg.get('endPercent', 100)
        name = seg.get('name', 'Unknown')
        direction = seg.get('direction', 'up')
        active = seg.get('active', True)
        keys = seg.get('keysChecked', 0)
        
        # Вычислить позицию на шкале
        start_pos = int((start / 100.0) * (width - 2))
        end_pos = int((end / 100.0) * (width - 2))
        
        # Создать визуализацию
        line = [' '] * width
        
        if start_pos < end_pos:
            # Направление вверх
            for i in range(start_pos, min(end_pos, width)):
                line[i] = '█' if active else '░'
            if start_pos < width:
                line[start_pos] = '▶'
        else:
            # Направление вниз
            for i in range(end_pos, min(start_pos + 1, width)):
                line[i] = '█' if active else '░'
            if start_pos < width:
                line[start_pos] = '◀'
        
        print(''.join(line))
        
        # Информация о сегменте
        status = "АКТИВЕН" if active else "ЗАВЕРШЁН"
        info = f"  {name:20s} {start:5.1f}%->{end:5.1f}% {direction:4s} [{status}] {keys:,} keys"
        print(info)
        print()

def visualize_progress_bar(total_keys: int, segment_keys: List[int], width: int = 50):
    """Прогресс-бар для общего прогресса"""
    print("\nОБЩИЙ ПРОГРЕСС:")
    print("─" * (width + 10))
    
    if not segment_keys or sum(segment_keys) == 0:
        print("[" + " " * width + "] 0%")
        return
    
    total = sum(segment_keys)
    filled = int((total / (total + 1)) * width)  # +1 чтобы избежать деления на 0
    
    bar = "█" * filled + "░" * (width - filled)
    percent = (total / max(total, 1)) * 100
    
    print(f"[{bar}] {total:,} ключей")

def format_time(seconds: int) -> str:
    """Форматировать время"""
    if seconds < 60:
        return f"{seconds}с"
    elif seconds < 3600:
        return f"{seconds // 60}м {seconds % 60}с"
    elif seconds < 86400:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}ч {mins}м"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}дн {hours}ч"

def print_statistics(progress: Dict):
    """Вывести статистику"""
    import time
    
    print("\n" + "=" * 80)
    print("СТАТИСТИКА")
    print("=" * 80)
    
    print(f"Битовый диапазон:    {progress['bitRange']}")
    print(f"Целевой адрес:       {progress['targetAddress']}")
    print(f"Всего ключей:        {progress['totalKeysChecked']:,}")
    
    if progress['startTime'] > 0:
        elapsed = int(time.time()) - progress['startTime']
        print(f"Время работы:        {format_time(elapsed)}")
        
        if elapsed > 0:
            rate = progress['totalKeysChecked'] / elapsed
            print(f"Средняя скорость:    {rate / 1_000_000:.2f} MKey/s")
    
    print(f"\nАктивных сегментов:  ", end="")
    active_count = sum(1 for seg in progress['segments'] if seg.get('active', False))
    print(f"{active_count}/{len(progress['segments'])}")
    
    print("\nРаспределение по сегментам:")
    for seg in progress['segments']:
        name = seg.get('name', 'Unknown')
        keys = seg.get('keysChecked', 0)
        active = "✓" if seg.get('active', False) else "✗"
        print(f"  {active} {name:20s} {keys:15,} ключей")

def main():
    parser = argparse.ArgumentParser(
        description="Визуализация прогресса сегментированного поиска"
    )
    parser.add_argument("progress_file", nargs='?', 
                       default="vanitysearch_progress.dat",
                       help="Файл прогресса (default: vanitysearch_progress.dat)")
    parser.add_argument("--stats-only", action="store_true",
                       help="Только статистика без визуализации")
    parser.add_argument("--watch", type=int, metavar="SECONDS",
                       help="Режим мониторинга с обновлением каждые N секунд")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.progress_file):
        print(f"❌ Файл прогресса не найден: {args.progress_file}")
        print("\nВозможные причины:")
        print("  - Поиск ещё не запущен")
        print("  - Сохранение прогресса не включено (-progress)")
        print("  - Неверный путь к файлу")
        sys.exit(1)
    
    if args.watch:
        import time
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')
                progress = parse_progress_file(args.progress_file)
                
                if not args.stats_only:
                    visualize_segments_ascii(progress['segments'])
                
                print_statistics(progress)
                
                print(f"\n🔄 Обновление каждые {args.watch} секунд... (Ctrl+C для выхода)")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n\nМониторинг остановлен.")
            sys.exit(0)
    else:
        progress = parse_progress_file(args.progress_file)
        
        if not args.stats_only:
            visualize_segments_ascii(progress['segments'])
        
        print_statistics(progress)

if __name__ == "__main__":
    main()

