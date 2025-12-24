#!/usr/bin/env python3
"""
Генерация позиционной маски на основе анализа найденных адресов
Анализирует ВСЕ позиции, а не только префикс
"""

import sys
import re
from collections import Counter

def extract_addresses(output_file: str) -> list:
    """Извлечь все найденные адреса"""
    addresses = []
    try:
        with open(output_file, 'r') as f:
            for line in f:
                addr_match = re.search(r'^PubAddress:\s+(1[A-Za-z0-9]+)', line)
                if addr_match:
                    addresses.append(addr_match.group(1))
    except FileNotFoundError:
        print(f"⚠️  Файл {output_file} не найден")
    
    return addresses

def find_best_matching_addresses(addresses: list, target: str, min_match: int = 5) -> list:
    """
    Найти адреса с хорошим совпадением с целевым
    Возвращает список (адрес, количество_совпадений)
    """
    best_matches = []
    
    for addr in addresses:
        match_count = 0
        for i in range(min(len(addr), len(target))):
            if addr[i] == target[i]:
                match_count += 1
            else:
                break
        
        if match_count >= min_match:
            best_matches.append((addr, match_count))
    
    # Сортировать по количеству совпадений
    best_matches.sort(key=lambda x: x[1], reverse=True)
    
    return best_matches

def analyze_positions(addresses: list, target: str, min_confidence: float = 0.1, min_match: int = 5) -> dict:
    """
    Анализировать все позиции адресов
    Сначала фильтрует адреса с хорошим совпадением, затем анализирует позиции
    Возвращает словарь: {позиция: (символ, частота_совпадения_с_целью)}
    """
    if not addresses:
        return {}
    
    # Найти адреса с хорошим совпадением
    best_matches = find_best_matching_addresses(addresses, target, min_match)
    
    if not best_matches:
        return {}
    
    print(f"   Используем {len(best_matches)} адресов с совпадением >= {min_match} символов")
    
    # Статистика по позициям (только для хороших совпадений)
    position_stats = {}  # {позиция: Counter({символ: количество_совпадений_с_целью})}
    
    for addr, match_count in best_matches:
        for pos in range(min(len(addr), len(target))):
            if pos not in position_stats:
                position_stats[pos] = Counter()
            
            # Если символ в этой позиции совпадает с целевым
            if addr[pos] == target[pos]:
                position_stats[pos][addr[pos]] += 1
    
    # Найти наиболее частые совпадения для каждой позиции
    result = {}
    for pos in sorted(position_stats.keys()):
        counter = position_stats[pos]
        if counter:
            most_common = counter.most_common(1)[0]
            char, count = most_common
            confidence = count / len(best_matches)  # Относительно хороших совпадений
            
            # Если уверенность достаточно высока, фиксируем символ
            if confidence >= min_confidence:
                result[pos] = (char, confidence, count)
    
    return result

def create_positional_mask(target: str, position_fixes: dict) -> str:
    """
    Создать позиционную маску на основе фиксированных позиций
    """
    mask = list(target)
    
    # Заменить все символы на звездочки
    for i in range(len(mask)):
        mask[i] = '*'
    
    # Установить фиксированные символы
    for pos, (char, confidence, count) in position_fixes.items():
        if pos < len(mask):
            mask[pos] = char
    
    return ''.join(mask)

def main():
    if len(sys.argv) < 3:
        print("Использование: python3 generate_positional_mask.py <output_file> <target_address> [min_confidence]")
        print("Пример: python3 generate_positional_mask.py iter1_results.txt 1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU 0.05")
        sys.exit(1)
    
    output_file = sys.argv[1]
    target = sys.argv[2]
    min_confidence = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
    
    print(f"🎯 Целевой адрес: {target}")
    print(f"📁 Файл результатов: {output_file}")
    print(f"📊 Минимальная уверенность: {min_confidence*100:.1f}%")
    print()
    
    # Извлечь адреса
    addresses = extract_addresses(output_file)
    
    if not addresses:
        print("❌ Адреса не найдены")
        sys.exit(1)
    
    print(f"✅ Найдено {len(addresses)} адресов")
    
    # Анализировать позиции
    print(f"\n🔍 Анализ позиций (используем только адреса с хорошим совпадением)...")
    position_fixes = analyze_positions(addresses, target, min_confidence, min_match=5)
    
    if not position_fixes:
        print("❌ Не найдено достаточно совпадений для создания маски")
        sys.exit(1)
    
    print(f"\n📊 Найдено {len(position_fixes)} фиксированных позиций:")
    print("   Позиция | Символ | Уверенность | Количество совпадений")
    print("   " + "-" * 60)
    
    for pos in sorted(position_fixes.keys()):
        char, confidence, count = position_fixes[pos]
        print(f"   {pos:8d} | {char:6s} | {confidence*100:10.2f}% | {count:20d}")
    
    # Создать позиционную маску
    mask = create_positional_mask(target, position_fixes)
    
    print(f"\n🎯 Сгенерированная позиционная маска:")
    print(f"   {mask}")
    print(f"\n📈 Статистика:")
    print(f"   Всего позиций: {len(target)}")
    print(f"   Фиксированных: {len(position_fixes)}")
    print(f"   Звездочек: {mask.count('*')}")
    print(f"   Покрытие: {len(position_fixes)*100/len(target):.1f}%")
    
    # Показать сравнение
    print(f"\n📋 Сравнение:")
    print(f"   Цель:     {target}")
    print(f"   Маска:    {mask}")
    
    # Сохранить маску в файл
    mask_file = "positional_mask.txt"
    with open(mask_file, 'w') as f:
        f.write(f"# Позиционная маска для Puzzle 71\n")
        f.write(f"# Сгенерировано на основе {len(addresses)} найденных адресов\n")
        f.write(f"# Фиксированных позиций: {len(position_fixes)}\n")
        f.write(f"# Минимальная уверенность: {min_confidence*100:.1f}%\n\n")
        f.write(f"{mask}\n")
    
    print(f"\n💾 Маска сохранена в: {mask_file}")
    print(f"\n💡 Следующий шаг:")
    print(f"   ./VanitySearch -bits 71 -kangaroo -seg segments_focused.txt '{mask}'")

if __name__ == "__main__":
    main()

