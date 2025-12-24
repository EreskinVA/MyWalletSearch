#!/usr/bin/env python3
"""
Глубокий анализ puzzle71_solution_table.csv
Поиск паттернов, закономерностей и оптимальных сегментов
"""

import csv
import re
from collections import Counter, defaultdict

def hex_to_decimal(hex_str):
    """Конвертировать hex в decimal"""
    try:
        return int(hex_str, 16)
    except:
        return None

def analyze_table_patterns(csv_file):
    """Анализ таблицы для поиска паттернов"""
    target = '1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU'
    
    print("🔬 ГЛУБОКИЙ АНАЛИЗ ТАБЛИЦЫ РЕШЕНИЙ")
    print("=" * 80)
    
    # Собираем статистику
    addresses_with_prefix = []
    hex_keys = []
    decimal_keys = []
    best_matches = []
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            addr = row.get('Публичный ключ', '')
            hex_key = row.get('16 (hex)', '')
            dec_key = row.get('10 (decimal)', '')
            
            if addr.startswith('1PWo3'):
                addresses_with_prefix.append(addr)
                
                # Анализ совпадения с целевым
                score = 0
                for i in range(min(len(addr), len(target))):
                    if addr[i] == target[i]:
                        score += 1
                    else:
                        break
                
                if score >= 6:
                    best_matches.append({
                        'addr': addr,
                        'score': score,
                        'hex': hex_key,
                        'dec': dec_key
                    })
                
                # Собираем ключи
                if hex_key:
                    hex_keys.append(hex_key)
                if dec_key:
                    try:
                        decimal_keys.append(int(dec_key))
                    except:
                        pass
    
    print(f"✅ Найдено {len(addresses_with_prefix)} адресов с префиксом '1PWo3'")
    print(f"✅ Найдено {len(best_matches)} адресов с совпадением >= 6 символов")
    
    if best_matches:
        print("\n📊 ТОП-10 ЛУЧШИХ СОВПАДЕНИЙ:")
        best_matches.sort(key=lambda x: x['score'], reverse=True)
        for i, match in enumerate(best_matches[:10], 1):
            print(f"   {i:2d}. {match['addr'][:45]:45s} | Совпадение: {match['score']} | Hex: {match['hex'][:20]}...")
    
    # Анализ распределения ключей
    if decimal_keys:
        decimal_keys.sort()
        min_key = decimal_keys[0]
        max_key = decimal_keys[-1]
        
        # Конвертация в проценты Puzzle 71
        puzzle_start = 2**70
        puzzle_end = 2**71 - 1
        puzzle_size = puzzle_end - puzzle_start
        
        min_percent = ((min_key - puzzle_start) / puzzle_size) * 100
        max_percent = ((max_key - puzzle_start) / puzzle_size) * 100
        
        print(f"\n📈 АНАЛИЗ ДИАПАЗОНА КЛЮЧЕЙ:")
        print(f"   Min: {min_percent:.8f}%")
        print(f"   Max: {max_percent:.8f}%")
        print(f"   Размер: {max_percent - min_percent:.8f}%")
        
        # Найти ключ с лучшим совпадением
        if best_matches:
            best_match = best_matches[0]
            best_hex = best_match['hex']
            best_dec = hex_to_decimal(best_hex)
            
            if best_dec:
                best_percent = ((best_dec - puzzle_start) / puzzle_size) * 100
                print(f"\n🎯 КЛЮЧ С ЛУЧШИМ СОВПАДЕНИЕМ ({best_match['score']} символов):")
                print(f"   Hex: {best_hex}")
                print(f"   Decimal: {best_dec:,}")
                print(f"   Позиция: {best_percent:.8f}%")
                
                return {
                    'best_percent': best_percent,
                    'best_hex': best_hex,
                    'best_score': best_match['score'],
                    'range_min': min_percent,
                    'range_max': max_percent
                }
    
    return None

def create_optimized_segments(analysis_result, expansion=0.01):
    """Создать оптимизированные сегменты вокруг лучшего совпадения"""
    if not analysis_result:
        return None
    
    best_percent = analysis_result['best_percent']
    
    # Расширяем диапазон вокруг лучшего совпадения
    min_percent = max(0, best_percent - expansion)
    max_percent = min(100, best_percent + expansion)
    
    # Создаем 8 сегментов
    num_segments = 8
    segment_size = (max_percent - min_percent) / num_segments
    
    segments = []
    for i in range(num_segments):
        start = min_percent + i * segment_size
        end = min_percent + (i + 1) * segment_size
        name = f"optimized_{i+1}"
        segments.append((start, end, name))
    
    return segments

def main():
    csv_file = 'puzzle71_solution_table.csv'
    
    analysis = analyze_table_patterns(csv_file)
    
    if analysis:
        print("\n" + "=" * 80)
        print("🎯 СОЗДАНИЕ ОПТИМИЗИРОВАННЫХ СЕГМЕНТОВ")
        print("=" * 80)
        
        segments = create_optimized_segments(analysis, expansion=0.01)
        
        if segments:
            output_file = 'segments_optimized.txt'
            with open(output_file, 'w') as f:
                f.write("# ========================================================================\n")
                f.write("# ОПТИМИЗИРОВАННЫЕ СЕГМЕНТЫ - на основе анализа таблицы решений\n")
                f.write("# ========================================================================\n")
                f.write(f"# Лучшее совпадение: {analysis['best_score']} символов\n")
                f.write(f"# Позиция: {analysis['best_percent']:.8f}%\n")
                f.write(f"# Диапазон: ±0.01% вокруг лучшего совпадения\n")
                f.write("# ========================================================================\n\n")
                
                for start, end, name in segments:
                    f.write(f"{start:.12f} {end:.12f} up {name}\n")
                
                f.write("\n# ========================================================================\n")
            
            print(f"\n✅ Сегменты сохранены в: {output_file}")
            print(f"\n📋 Создано {len(segments)} сегментов:")
            for i, (start, end, name) in enumerate(segments, 1):
                print(f"   {i}. {name}: {start:.8f}% - {end:.8f}%")
            
            print(f"\n💡 РЕКОМЕНДАЦИЯ:")
            print(f"   Используйте маску '1PWo3JeB9j*' для поиска")
            print(f"   Запуск: ./VanitySearch -seg {output_file} -bits 71 -kangaroo -t 4 '1PWo3JeB9j*'")

if __name__ == "__main__":
    main()

