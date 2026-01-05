#!/usr/bin/env python3
"""
Анализатор найденных адресов для инкрементального поиска
Сравнивает найденные адреса с целевым и предлагает следующий шаг
"""

import sys
import re
from typing import List, Tuple, Optional

def extract_addresses(output_file: str) -> List[str]:
    """Извлечь все найденные адреса из файла результатов"""
    addresses = []
    try:
        with open(output_file, 'r') as f:
            for line in f:
                # Ищем строки вида "PubAddress: 1ABC..."
                match = re.search(r'^PubAddress:\s+(1[A-Za-z0-9]+)', line)
                if match:
                    addresses.append(match.group(1))
    except FileNotFoundError:
        print(f"⚠️  Файл {output_file} не найден")
    return addresses

def compare_addresses(found: str, target: str) -> Tuple[int, str]:
    """
    Сравнить найденный адрес с целевым
    Возвращает: (количество совпадающих символов, описание различий)
    """
    min_len = min(len(found), len(target))
    matches = 0
    
    for i in range(min_len):
        if found[i] == target[i]:
            matches += 1
        else:
            break
    
    diff_info = ""
    if matches < len(target):
        if matches < len(found):
            diff_info = f"На позиции {matches}: '{found[matches]}' вместо '{target[matches]}'"
        else:
            diff_info = f"Адрес короче целевого (не хватает символов)"
    
    return matches, diff_info

def analyze_results(output_file: str, target: str) -> Optional[Tuple[str, int]]:
    """Проанализировать результаты и найти лучшее совпадение"""
    addresses = extract_addresses(output_file)
    
    if not addresses:
        print("❌ Адреса не найдены")
        return None
    
    print(f"📊 Найдено адресов: {len(addresses)}")
    print("=" * 60)
    
    best_match = None
    best_score = 0
    best_info = ""
    
    for addr in addresses:
        score, info = compare_addresses(addr, target)
        print(f"  {addr[:40]}... | Совпадение: {score}/{len(target)} символов")
        if info:
            print(f"    └─ {info}")
        
        if score > best_score:
            best_score = score
            best_match = addr
            best_info = info
    
    print("=" * 60)
    
    if best_match:
        print(f"✅ Лучшее совпадение: {best_match}")
        print(f"   Совпадение: {best_score}/{len(target)} символов ({best_score*100//len(target)}%)")
        if best_info:
            print(f"   {best_info}")
        return (best_match, best_score)
    
    return None

def suggest_next_step(best_score: int, current_prefix: str, current_suffix: str, target: str):
    """Предложить следующий шаг поиска"""
    print("\n💡 Рекомендации для следующего шага:")
    print("=" * 60)
    
    if best_score >= len(target):
        print("🎉 Целевой адрес найден!")
        return
    
    # Определяем позицию следующего символа
    next_pos = best_score
    
    # Определяем, увеличивать префикс или суффикс
    prefix_end = len(current_prefix)
    suffix_start = len(target) - len(current_suffix)
    
    if next_pos < prefix_end:
        # Увеличиваем префикс
        new_prefix = target[:next_pos + 1]
        print(f"1. Увеличить префикс: {new_prefix}*{current_suffix}")
        print(f"   Текущий: {current_prefix}*{current_suffix}")
        print(f"   Новый:   {new_prefix}*{current_suffix}")
    elif next_pos < suffix_start:
        # Увеличиваем префикс до нужной позиции
        new_prefix = target[:next_pos + 1]
        print(f"2. Увеличить префикс: {new_prefix}*{current_suffix}")
        print(f"   Текущий: {current_prefix}*{current_suffix}")
        print(f"   Новый:   {new_prefix}*{current_suffix}")
    else:
        # Увеличиваем суффикс
        suffix_len = len(target) - next_pos
        new_suffix = target[-suffix_len:]
        print(f"3. Увеличить суффикс: {current_prefix}*{new_suffix}")
        print(f"   Текущий: {current_prefix}*{current_suffix}")
        print(f"   Новый:   {current_prefix}*{new_suffix}")
    
    print("=" * 60)

def main():
    if len(sys.argv) < 3:
        print("Использование: python3 analyze_found_addresses.py <output_file> <target_address>")
        print("Пример: python3 analyze_found_addresses.py incremental_results.txt 1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU")
        sys.exit(1)
    
    output_file = sys.argv[1]
    target = sys.argv[2]
    
    print(f"🎯 Целевой адрес: {target}")
    print(f"📁 Файл результатов: {output_file}")
    print()
    
    result = analyze_results(output_file, target)
    
    if result:
        best_match, best_score = result
        # Определить текущий префикс и суффикс из контекста
        # Для простоты используем фиксированные значения
        current_prefix = "1PWo3Je"  # Можно сделать параметром
        current_suffix = "zXU"      # Можно сделать параметром
        suggest_next_step(best_score, current_prefix, current_suffix, target)

if __name__ == "__main__":
    main()

