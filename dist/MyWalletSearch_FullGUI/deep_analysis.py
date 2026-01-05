#!/usr/bin/env python3
"""
Глубокий анализ найденных адресов + puzzle71_solution_table.csv
Подход: Cryptographer + Hacker + Researcher
"""

import sys
import re
import csv
from collections import Counter, defaultdict
from typing import List, Tuple, Dict

def extract_addresses_from_results(file: str) -> List[str]:
    """Извлечь адреса из файла результатов VanitySearch"""
    addresses = []
    try:
        with open(file, 'r') as f:
            for line in f:
                match = re.search(r'^PubAddress:\s+(1[A-Za-z0-9]+)', line)
                if match:
                    addresses.append(match.group(1))
    except FileNotFoundError:
        print(f"⚠️  Файл {file} не найден")
    return addresses

def load_solution_table(csv_file: str) -> List[Dict]:
    """Загрузить таблицу решений из CSV"""
    results = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
    except FileNotFoundError:
        print(f"⚠️  Файл {csv_file} не найден")
    return results

def analyze_position_patterns(addresses: List[str], target: str) -> Dict[int, Counter]:
    """
    Анализ паттернов по позициям
    Возвращает словарь: {позиция: Counter({символ: частота})}
    """
    position_stats = defaultdict(Counter)
    
    for addr in addresses:
        for pos in range(min(len(addr), len(target))):
            if addr[pos] == target[pos]:
                # Символ совпадает с целевым
                position_stats[pos][addr[pos]] += 1
    
    return position_stats

def find_intermediate_matches(addresses: List[str], target: str, min_confidence: float = 0.05) -> Dict[int, Tuple[str, float, int]]:
    """
    Найти промежуточные совпадения с целевым адресом
    Возвращает: {позиция: (символ, уверенность, количество)}
    """
    if not addresses:
        return {}
    
    # Фильтровать только адреса, начинающиеся с '1PWo3'
    relevant = [a for a in addresses if a.startswith('1PWo3')]
    
    if not relevant:
        return {}
    
    position_stats = analyze_position_patterns(relevant, target)
    
    result = {}
    total = len(relevant)
    
    for pos in sorted(position_stats.keys()):
        counter = position_stats[pos]
        if counter:
            most_common = counter.most_common(1)[0]
            char, count = most_common
            confidence = count / total
            
            if confidence >= min_confidence:
                result[pos] = (char, confidence, count)
    
    return result

def analyze_solution_table_for_patterns(csv_data: List[Dict], target: str) -> Dict:
    """
    Анализ таблицы решений для поиска паттернов
    """
    # Найти адреса в таблице, которые близки к целевому
    close_matches = []
    
    for row in csv_data:
        # Предполагаем, что адрес в одной из колонок
        for key, value in row.items():
            if isinstance(value, str) and value.startswith('1'):
                # Это похоже на адрес
                score = 0
                for i in range(min(len(value), len(target))):
                    if value[i] == target[i]:
                        score += 1
                    else:
                        break
                
                if score >= 5:  # Совпадение >= 5 символов
                    close_matches.append({
                        'address': value,
                        'score': score,
                        'row': row
                    })
    
    return {
        'close_matches': close_matches,
        'count': len(close_matches)
    }

def cross_reference_with_table(found_addresses: List[str], csv_data: List[Dict], target: str):
    """
    Перекрестная проверка найденных адресов с таблицей решений
    """
    # Найти адреса из таблицы, которые совпадают с найденными
    table_addresses = set()
    for row in csv_data:
        for key, value in row.items():
            if isinstance(value, str) and value.startswith('1'):
                table_addresses.add(value)
    
    found_set = set(found_addresses)
    intersection = found_set & table_addresses
    
    return {
        'found_in_table': list(intersection),
        'count': len(intersection)
    }

def main():
    target = '1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU'
    results_file = 'final_combined.txt'
    csv_file = 'puzzle71_solution_table.csv'
    
    print("=" * 80)
    print("🔬 ГЛУБОКИЙ АНАЛИЗ: CRYPTOGRAPHER + HACKER + RESEARCHER")
    print("=" * 80)
    print(f"🎯 Целевой адрес: {target}")
    print()
    
    # 1. Загрузить найденные адреса
    print("📥 Загрузка данных...")
    found_addresses = extract_addresses_from_results(results_file)
    print(f"   ✅ Найдено {len(found_addresses)} адресов в результатах поиска")
    
    # 2. Загрузить таблицу решений
    csv_data = load_solution_table(csv_file)
    print(f"   ✅ Загружено {len(csv_data)} записей из таблицы решений")
    print()
    
    # 3. Анализ промежуточных совпадений с низким порогом
    print("🔍 АНАЛИЗ 1: Поиск промежуточных символов (порог 5-8%)")
    print("-" * 80)
    
    for threshold in [0.05, 0.06, 0.07, 0.08]:
        matches = find_intermediate_matches(found_addresses, target, threshold)
        if matches:
            print(f"\n📊 Порог уверенности: {threshold*100:.0f}%")
            print("   Позиция | Символ | Уверенность | Количество")
            print("   " + "-" * 50)
            for pos in sorted(matches.keys()):
                char, conf, count = matches[pos]
                print(f"   {pos:8d} | {char:6s} | {conf*100:10.2f}% | {count:10d}")
    
    # 4. Анализ таблицы решений
    print("\n" + "=" * 80)
    print("🔍 АНАЛИЗ 2: Анализ таблицы решений")
    print("-" * 80)
    
    table_analysis = analyze_solution_table_for_patterns(csv_data, target)
    print(f"📊 Найдено {table_analysis['count']} адресов в таблице с совпадением >= 5 символов")
    
    if table_analysis['close_matches']:
        print("\n📋 Топ-10 ближайших совпадений из таблицы:")
        sorted_matches = sorted(table_analysis['close_matches'], key=lambda x: x['score'], reverse=True)
        for i, match in enumerate(sorted_matches[:10], 1):
            addr = match['address']
            score = match['score']
            print(f"   {i:2d}. {addr[:50]:50s} | Совпадение: {score} символов")
    
    # 5. Перекрестная проверка
    print("\n" + "=" * 80)
    print("🔍 АНАЛИЗ 3: Перекрестная проверка")
    print("-" * 80)
    
    cross_ref = cross_reference_with_table(found_addresses, csv_data, target)
    print(f"📊 Найдено {cross_ref['count']} адресов, присутствующих и в результатах, и в таблице")
    
    if cross_ref['found_in_table']:
        print("\n✅ Адреса, найденные в обоих источниках:")
        for addr in cross_ref['found_in_table'][:10]:
            print(f"   {addr}")
    
    # 6. Генерация улучшенной маски
    print("\n" + "=" * 80)
    print("🎯 ГЕНЕРАЦИЯ УЛУЧШЕННОЙ ПОЗИЦИОННОЙ МАСКИ")
    print("-" * 80)
    
    # Использовать порог 6% для баланса между точностью и покрытием
    final_matches = find_intermediate_matches(found_addresses, target, 0.06)
    
    if final_matches:
        mask = list(target)
        for i in range(len(mask)):
            mask[i] = '*'
        
        for pos, (char, conf, count) in final_matches.items():
            if pos < len(mask):
                mask[pos] = char
        
        mask_str = ''.join(mask)
        
        print(f"\n✅ Сгенерированная маска (порог 6%):")
        print(f"   {mask_str}")
        print(f"\n📈 Статистика:")
        print(f"   Фиксированных позиций: {len(final_matches)}")
        print(f"   Покрытие: {len(final_matches)*100/len(target):.1f}%")
        
        # Сохранить маску
        with open('positional_mask_improved.txt', 'w') as f:
            f.write(f"# Улучшенная позиционная маска (порог 6%)\n")
            f.write(f"# Сгенерировано на основе {len(found_addresses)} найденных адресов\n")
            f.write(f"# Фиксированных позиций: {len(final_matches)}\n\n")
            f.write(f"{mask_str}\n")
        
        print(f"\n💾 Маска сохранена в: positional_mask_improved.txt")

if __name__ == "__main__":
    main()

