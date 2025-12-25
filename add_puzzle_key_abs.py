#!/usr/bin/env python3
"""
Добавляет PuzzleKeyAbs (DEC) в старые out-файлы на основе Priv (DEC).

Логика:
- Если Priv (DEC) попадает в диапазон puzzle71 (2^70 .. 2^71-1), используем его как PuzzleKeyAbs
- Если Priv (DEC) очень большой (после endomorphism), пропускаем (нет способа восстановить оригинальный ключ)

Использование:
  python3 add_puzzle_key_abs.py out_cpu_p1.txt out_cpu_p2.txt out_cpu_p3.txt
  (или без аргументов - обработает все out_cpu_p*.txt)
"""

import sys
import re
from pathlib import Path

# Диапазон puzzle71
PUZZLE71_MIN = 2**70
PUZZLE71_MAX = 2**71 - 1


def add_puzzle_key_abs_to_file(filepath):
    """Добавить PuzzleKeyAbs (DEC) в файл если его нет."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"⚠ Файл не найден: {filepath}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠ Ошибка чтения {filepath}: {e}", file=sys.stderr)
        return False
    
    # Проверяем, есть ли уже PuzzleKeyAbs
    if "PuzzleKeyAbs (DEC):" in content:
        print(f"✓ {filepath}: уже содержит PuzzleKeyAbs, пропускаем", file=sys.stderr)
        return True
    
    # Находим все блоки с Priv (DEC)
    pattern = r'(PubAddress: .+?Priv \(DEC\): (\d+))'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    if not matches:
        print(f"⚠ {filepath}: не найдено Priv (DEC), пропускаем", file=sys.stderr)
        return False
    
    # Собираем строки с заменой
    result_lines = []
    i = 0
    last_pos = 0
    
    for match in matches:
        # Добавляем текст до блока
        result_lines.append(content[last_pos:match.start()])
        
        full_match = match.group(1)
        priv_dec = int(match.group(2))
        
        # Проверяем попадает ли в диапазон puzzle71
        if PUZZLE71_MIN <= priv_dec <= PUZZLE71_MAX:
            # Это и есть PuzzleKeyAbs!
            puzzle_key_abs = priv_dec
            # Добавляем блок + новую строку PuzzleKeyAbs
            result_lines.append(full_match)
            result_lines.append(f"\nPuzzleKeyAbs (DEC): {puzzle_key_abs}\n")
            i += 1
        else:
            # Очень большой ключ (после endomorphism) - пропускаем
            result_lines.append(full_match)
        
        last_pos = match.end()
    
    # Добавляем остаток файла
    result_lines.append(content[last_pos:])
    
    # Создаём backup и записываем
    backup_path = str(filepath) + ".bak"
    try:
        with open(backup_path, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"⚠ Не удалось создать backup: {e}", file=sys.stderr)
        return False
    
    try:
        new_content = ''.join(result_lines)
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"✓ {filepath}: добавлено {i} PuzzleKeyAbs (backup: {backup_path})", file=sys.stderr)
        return True
    except Exception as e:
        print(f"⚠ Ошибка записи {filepath}: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        # Автоматически находим все out_cpu_p*.txt
        files = sorted(Path('.').glob('out_cpu_p*.txt'))
        files = [str(f) for f in files]
    
    if not files:
        print("Ошибка: не найдено файлов для обработки", file=sys.stderr)
        sys.exit(1)
    
    print(f"Обработка {len(files)} файлов...", file=sys.stderr)
    print("", file=sys.stderr)
    
    success_count = 0
    for filepath in files:
        if add_puzzle_key_abs_to_file(filepath):
            success_count += 1
    
    print("", file=sys.stderr)
    print(f"Готово: обработано {success_count}/{len(files)} файлов", file=sys.stderr)


if __name__ == "__main__":
    main()

