#!/usr/bin/env python3
"""
Анализ найденных адресов и перестройка сегментов для фокусировки на перспективной области
"""

import sys
import re
from typing import List, Tuple, Optional

def extract_addresses_and_keys(output_file: str) -> List[Tuple[str, str]]:
    """Извлечь найденные адреса и их приватные ключи"""
    results = []
    current_addr = None
    current_key = None
    
    try:
        with open(output_file, 'r') as f:
            for line in f:
                # Ищем адрес
                addr_match = re.search(r'^PubAddress:\s+(1[A-Za-z0-9]+)', line)
                if addr_match:
                    current_addr = addr_match.group(1)
                
                # Ищем приватный ключ (HEX)
                key_match = re.search(r'^Priv\s+\(HEX\):\s+0x([A-Fa-f0-9]+)', line)
                if key_match:
                    current_key = key_match.group(1)
                    if current_addr:
                        results.append((current_addr, current_key))
                        current_addr = None
                        current_key = None
    except FileNotFoundError:
        print(f"⚠️  Файл {output_file} не найден")
    
    return results

def hex_to_decimal(hex_str: str) -> int:
    """Конвертировать hex в decimal"""
    return int(hex_str, 16)

def analyze_key_range(results: List[Tuple[str, str]], target: str) -> Optional[Tuple[int, int, int]]:
    """
    Анализировать диапазон ключей найденных адресов
    Возвращает: (min_key, max_key, best_match_score) или None
    """
    if not results:
        return None
    
    # Найти лучшее совпадение с целевым адресом
    best_score = 0
    best_key = None
    best_addr = None
    
    keys_decimal = []
    
    for addr, key_hex in results:
        # Сравнить адрес с целевым
        score = 0
        for i in range(min(len(addr), len(target))):
            if addr[i] == target[i]:
                score += 1
            else:
                break
        
        if score > best_score:
            best_score = score
            best_key = key_hex
            best_addr = addr
        
        # Конвертировать ключ в decimal
        try:
            key_dec = hex_to_decimal(key_hex)
            keys_decimal.append((key_dec, addr, score))
        except ValueError:
            continue
    
    if not keys_decimal:
        return None
    
    # Найти min и max ключи
    keys_only = [k[0] for k in keys_decimal]
    min_key = min(keys_only)
    max_key = max(keys_only)
    
    # Фильтровать только адреса с хорошими совпадениями (>= 5 символов для лучшей точности)
    good_matches = [k for k in keys_decimal if k[2] >= 5]
    
    if not good_matches:
        # Если нет хороших совпадений >=5, попробуем >=4
        good_matches = [k for k in keys_decimal if k[2] >= 4]
    
    if not good_matches:
        # Если все еще нет, использовать все
        good_matches = keys_decimal
    
    # Найти ключи с лучшими совпадениями (top 20 или top 10%)
    good_matches.sort(key=lambda x: x[2], reverse=True)
    top_count = min(20, max(10, len(good_matches) // 10))  # Top 20 или top 10%
    top_keys = good_matches[:top_count]
    top_keys_only = [k[0] for k in top_keys]
    
    print(f"\n🔍 Анализ топ-{len(top_keys)} совпадений (>=4 символов):")
    for i, (key_dec, addr, score) in enumerate(top_keys[:5], 1):  # Показать топ-5
        print(f"   {i}. {addr[:45]}... | Совпадение: {score} | Ключ: {key_dec:,}")
    
    # Создать фокусированный диапазон вокруг лучших совпадений
    if top_keys_only and len(top_keys_only) > 1:
        focus_min = min(top_keys_only)
        focus_max = max(top_keys_only)
        # Расширить диапазон на 100% в каждую сторону для безопасности
        range_size = focus_max - focus_min
        if range_size > 0:
            expanded_min = max(min_key, focus_min - range_size)
            expanded_max = min(max_key, focus_max + range_size)
        else:
            # Если все ключи одинаковые, расширить на 1% от общего диапазона
            total_range = max_key - min_key
            expanded_min = max(min_key, focus_min - total_range // 200)
            expanded_max = min(max_key, focus_max + total_range // 200)
    elif top_keys_only:
        # Если только один ключ, расширить на 1% от общего диапазона
        total_range = max_key - min_key
        center = top_keys_only[0]
        expanded_min = max(min_key, center - total_range // 200)
        expanded_max = min(max_key, center + total_range // 200)
    else:
        # Если нет хороших совпадений, использовать весь диапазон лучших ключей
        expanded_min = min_key
        expanded_max = max_key
    
    print(f"\n📊 Анализ диапазона ключей:")
    print(f"   Всего найдено: {len(keys_decimal)} адресов")
    print(f"   Диапазон ключей: {min_key} - {max_key}")
    print(f"   Размер диапазона: {max_key - min_key:,}")
    
    if best_addr and best_key:
        best_key_dec = hex_to_decimal(best_key)
        print(f"\n✅ Лучшее совпадение:")
        print(f"   Адрес: {best_addr}")
        print(f"   Ключ (hex): 0x{best_key}")
        print(f"   Ключ (dec): {best_key_dec:,}")
        print(f"   Совпадение: {best_score}/{len(target)} символов ({best_score*100//len(target)}%)")
    
    if top_keys_only:
        print(f"\n🎯 Фокусированный диапазон (топ {len(top_keys)} совпадений):")
        print(f"   От: {expanded_min:,}")
        print(f"   До: {expanded_max:,}")
        print(f"   Размер: {expanded_max - expanded_min:,}")
    
    return (expanded_min, expanded_max, best_score)

def decimal_to_percent(decimal_key: int, bit_range: int = 71) -> float:
    """Конвертировать decimal ключ в процент от диапазона"""
    range_start = 2 ** (bit_range - 1)
    range_end = 2 ** bit_range - 1
    range_size = range_end - range_start
    
    if range_size == 0:
        return 0.0
    
    percent = ((decimal_key - range_start) / range_size) * 100.0
    return max(0.0, min(100.0, percent))

def create_focused_segments(min_key: int, max_key: int, bit_range: int = 71, num_segments: int = 5) -> List[Tuple[float, float, str]]:
    """
    Создать сфокусированные сегменты вокруг найденного диапазона
    Возвращает список (start_percent, end_percent, name)
    """
    range_start = 2 ** (bit_range - 1)
    range_end = 2 ** bit_range - 1
    
    # Конвертировать ключи в проценты
    min_percent = decimal_to_percent(min_key, bit_range)
    max_percent = decimal_to_percent(max_key, bit_range)
    
    # Расширить диапазон на 10% в каждую сторону для безопасности
    range_size = max_percent - min_percent
    expanded_min = max(0.0, min_percent - range_size * 0.1)
    expanded_max = min(100.0, max_percent + range_size * 0.1)
    
    # Разделить на сегменты
    segments = []
    segment_size = (expanded_max - expanded_min) / num_segments
    
    for i in range(num_segments):
        start = expanded_min + i * segment_size
        end = expanded_min + (i + 1) * segment_size
        name = f"focused_{i+1}"
        segments.append((start, end, name))
    
    return segments

def generate_segments_file(segments: List[Tuple[float, float, str]], output_file: str):
    """Генерировать файл сегментов"""
    with open(output_file, 'w') as f:
        f.write("# ========================================================================\n")
        f.write("# СФОКУСИРОВАННЫЕ СЕГМЕНТЫ - Автоматически сгенерировано\n")
        f.write("# ========================================================================\n")
        f.write("# Сегменты созданы на основе анализа найденных адресов\n")
        f.write("# для фокусировки поиска на перспективной области\n")
        f.write("# ========================================================================\n\n")
        
        for start, end, name in segments:
            f.write(f"{start:.12f} {end:.12f} up {name}\n")
        
        f.write("\n# ========================================================================\n")

def main():
    if len(sys.argv) < 3:
        print("Использование: python3 analyze_and_refine.py <output_file> <target_address> [bit_range]")
        print("Пример: python3 analyze_and_refine.py test_inc2_results.txt 1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU 71")
        sys.exit(1)
    
    output_file = sys.argv[1]
    target = sys.argv[2]
    bit_range = int(sys.argv[3]) if len(sys.argv) > 3 else 71
    
    print(f"🎯 Целевой адрес: {target}")
    print(f"📁 Файл результатов: {output_file}")
    print(f"🔢 Битовый диапазон: {bit_range}")
    print()
    
    # Извлечь адреса и ключи
    results = extract_addresses_and_keys(output_file)
    
    if not results:
        print("❌ Адреса не найдены в файле результатов")
        sys.exit(1)
    
    print(f"✅ Найдено {len(results)} адресов с ключами")
    
    # Анализировать диапазон
    range_info = analyze_key_range(results, target)
    
    if not range_info:
        print("❌ Не удалось проанализировать диапазон")
        sys.exit(1)
    
    # range_info содержит (expanded_min, expanded_max, best_score)
    # Это уже фокусированный диапазон вокруг лучших совпадений
    focus_min, focus_max, best_score = range_info
    
    # Создать сфокусированные сегменты на основе фокусированного диапазона
    segments = create_focused_segments(focus_min, focus_max, bit_range, num_segments=5)
    
    print(f"\n📋 Создано {len(segments)} сфокусированных сегментов:")
    for i, (start, end, name) in enumerate(segments, 1):
        print(f"   {i}. {name}: {start:.2f}% - {end:.2f}%")
    
    # Сохранить в файл
    output_segments = "segments_focused.txt"
    generate_segments_file(segments, output_segments)
    
    print(f"\n💾 Сегменты сохранены в: {output_segments}")
    print(f"\n💡 Следующий шаг:")
    print(f"   Используйте файл {output_segments} для следующего поиска:")
    print(f"   ./VanitySearch -seg {output_segments} -bits {bit_range} -kangaroo ...")

if __name__ == "__main__":
    main()

