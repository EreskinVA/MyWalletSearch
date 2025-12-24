#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обработки puzzle71_solution 2.txt и создания таблицы
с представлениями приватных ключей в разных системах счисления
"""

import base64
import sys
import string
import csv


def int_to_base(n, base, alphabet):
    """Преобразует целое число в строку в заданной системе счисления"""
    if n == 0:
        return alphabet[0]
    
    result = []
    while n > 0:
        result.append(alphabet[n % base])
        n //= base
    
    return ''.join(reversed(result))


def int_to_base2(n):
    """Преобразует число в двоичное представление"""
    return bin(n)[2:]  # убираем префикс '0b'


def int_to_base10(n):
    """Преобразует число в десятичное представление"""
    return str(n)


def int_to_base16(n):
    """Преобразует число в шестнадцатеричное представление"""
    return hex(n)[2:].upper()  # убираем префикс '0x'


def int_to_base32_custom(n):
    """Преобразует число в base32 (используя стандартный алфавит base32)"""
    # Стандартный алфавит base32: A-Z и 2-7
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
    return int_to_base(n, 32, alphabet)


def int_to_base64_custom(n):
    """Преобразует число в base64 (используя стандартный алфавит base64)"""
    # Стандартный алфавит base64: A-Z, a-z, 0-9, +, /
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + '+/'
    return int_to_base(n, 64, alphabet)


def int_to_base128_custom(n):
    """Преобразует число в base128"""
    # Используем алфавит из 128 символов
    # Комбинация: A-Z (26), a-z (26), 0-9 (10), специальные символы ASCII (32-126)
    # и расширенные символы до 128 символов
    base_ascii = string.ascii_uppercase + string.ascii_lowercase + string.digits
    special = ' !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    # Добавляем расширенные символы (латиница расширенная, греческие и др.)
    extended = ''.join(chr(i) for i in range(160, 288) if chr(i).isprintable())
    
    alphabet = (base_ascii + special + extended)[:128]
    # Если не хватает, дополняем повторением
    while len(alphabet) < 128:
        alphabet += base_ascii
    alphabet = alphabet[:128]
    
    result = int_to_base(n, 128, alphabet)
    return escape_for_table(result)


def escape_for_table(s):
    """Экранирует символы для безопасной записи в CSV (CSV модуль обработает это автоматически, но оставляем для совместимости)"""
    # CSV модуль сам обработает экранирование, но оставляем функцию для базовых преобразований
    result = []
    for char in s:
        code = ord(char)
        if code == ord('\n'):
            result.append('\\n')
        elif code == ord('\r'):
            result.append('\\r')
        elif 32 <= code < 127:  # Печатаемые ASCII
            result.append(char)
        elif code < 256:
            result.append(f'\\x{code:02x}')
        else:
            # Для Unicode символов используем \u
            result.append(f'\\u{code:04x}')
    return ''.join(result)


def int_to_base256_custom(n):
    """Преобразует число в base256"""
    # Для base256 представляем число как последовательность байтов
    # Преобразуем число в байты, затем каждому байту соответствует символ с кодом 0-255
    if n == 0:
        return '\\x00'
    
    # Конвертируем число в байты (big-endian)
    byte_count = (n.bit_length() + 7) // 8
    if byte_count == 0:
        byte_count = 1
    
    # Получаем байтовое представление
    bytes_repr = n.to_bytes(byte_count, byteorder='big')
    
    # Каждый байт преобразуем в символ (используем Latin-1 для всех 256 значений)
    result = bytes_repr.decode('latin-1')
    
    # Экранируем для безопасной записи в таблицу
    return escape_for_table(result)


def int_to_base512_custom(n):
    """Преобразует число в base512"""
    # Создаем алфавит из 512 символов
    # Используем комбинацию безопасных символов
    
    # Базовый набор: A-Z, a-z, 0-9 (62 символа)
    base_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    
    # Добавляем пунктуацию и специальные символы
    special_chars = ' !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    
    # Добавляем расширенные символы UTF-8 (латиница, греческие, кириллица и др.)
    extended_chars = ''.join(chr(i) for i in range(160, 1200) if chr(i).isprintable())
    
    # Объединяем и берем первые 512 символов
    alphabet = (base_chars + special_chars + extended_chars)[:512]
    
    # Если не хватает символов, дополняем повторением
    while len(alphabet) < 512:
        alphabet += base_chars
    
    alphabet = alphabet[:512]
    
    result = int_to_base(n, 512, alphabet)
    return escape_for_table(result)


def parse_file(input_file):
    """Парсит файл и извлекает данные о ключах"""
    keys = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        if lines[i].startswith('PubAddress:'):
            pub_address = lines[i].split(':', 1)[1].strip()
            i += 1
            
            if i < len(lines) and lines[i].startswith('Priv (WIF):'):
                wif = lines[i].split(':', 1)[1].strip()
                i += 1
                
                if i < len(lines) and lines[i].startswith('Priv (HEX):'):
                    hex_str = lines[i].split(':', 1)[1].strip()
                    # Убираем префикс '0x' если есть
                    if hex_str.startswith('0x'):
                        hex_str = hex_str[2:]
                    
                    # Преобразуем HEX в целое число
                    try:
                        priv_int = int(hex_str, 16)
                        keys.append({
                            'pub_address': pub_address,
                            'wif': wif,
                            'hex': hex_str,
                            'int': priv_int
                        })
                    except ValueError as e:
                        print(f"Ошибка при преобразовании HEX: {hex_str}, {e}", file=sys.stderr)
                        i += 1
                        continue
        
        i += 1
    
    return keys


def process_keys(keys, output_file):
    """Обрабатывает ключи и создает CSV таблицу"""
    
    # Сортируем ключи по возрастанию десятичного значения приватного ключа
    print("Сортирую ключи по возрастанию...", file=sys.stderr)
    keys_sorted = sorted(keys, key=lambda x: x['int'])
    
    # Заголовок таблицы
    header = ['Публичный ключ', 'Приватный (WIF)', '2 (binary)', '10 (decimal)', '16 (hex)', '32', '64', '128', '256', '512']
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        
        total = len(keys_sorted)
        for idx, key in enumerate(keys_sorted, 1):
            if idx % 100 == 0:
                print(f"Обработано {idx}/{total} записей...", file=sys.stderr)
            
            priv_int = key['int']
            
            # Преобразуем в разные системы счисления
            try:
                base2 = int_to_base2(priv_int)
                base10 = int_to_base10(priv_int)
                base16 = int_to_base16(priv_int)
                base32 = int_to_base32_custom(priv_int)
                base64_val = int_to_base64_custom(priv_int)
                base128 = int_to_base128_custom(priv_int)
                base256 = int_to_base256_custom(priv_int)
                base512 = int_to_base512_custom(priv_int)
                
                # Записываем строку в CSV
                row = [key['pub_address'], key['wif'], base2, base10, base16, base32, base64_val, base128, base256, base512]
                writer.writerow(row)
                
            except Exception as e:
                print(f"Ошибка при обработке ключа {key['pub_address']}: {e}", file=sys.stderr)
                continue


def main():
    input_file = '/Users/vladimirereskin/Projects/iiModel/VanitySearch/puzzle71_solution 2.txt'
    output_file = '/Users/vladimirereskin/Projects/iiModel/VanitySearch/puzzle71_solution_table.csv'
    
    print("Начинаю парсинг файла...", file=sys.stderr)
    keys = parse_file(input_file)
    print(f"Найдено {len(keys)} ключей", file=sys.stderr)
    
    print("Начинаю обработку ключей...", file=sys.stderr)
    process_keys(keys, output_file)
    print(f"Таблица сохранена в {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()

