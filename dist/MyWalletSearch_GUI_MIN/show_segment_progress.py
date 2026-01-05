#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальный просмотр прогресса по сегментам
Читает seg-файл для границ и progress-файл для текущих позиций
"""

import sys
import os
import re
import signal
from datetime import datetime

# Настройка кодировки для корректного вывода русского текста в Windows
if sys.platform == 'win32':
    try:
        # Переключаем консоль на UTF-8 (кодовая страница 65001)
        os.system('chcp 65001 >nul 2>&1')
    except Exception:
        pass
    
    try:
        # Пытаемся использовать UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        else:
            # Для старых версий Python
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        # Если не получилось, пробуем cp866 (DOS кодировка для русских символов)
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='cp866', errors='replace')
            else:
                import io
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='cp866', errors='replace')
        except Exception:
            pass

# Не печатать Traceback при использовании с пайпами (head/tail закрывают stdout рано)
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except Exception:
    pass

def infer_out_file(progress_file: str) -> str:
    """
    Пытается угадать out-файл по имени progress-файла.
    Примеры:
      progress_puzzle71_69_72.dat -> out_puzzle71_69_72.txt
      prog_cpu_p3.dat            -> out_cpu_p3.txt
    """
    base = os.path.basename(progress_file)
    # убираем расширение
    if base.endswith('.dat'):
        stem = base[:-4]
    else:
        stem = base

    candidates = []
    if stem.startswith('progress_'):
        candidates.append('out_' + stem[len('progress_'):] + '.txt')
    if stem.startswith('prog_'):
        candidates.append('out_' + stem[len('prog_'):] + '.txt')

    # общий случай: заменить progress->out
    if 'progress' in stem:
        candidates.append(stem.replace('progress', 'out') + '.txt')

    # fallback: out_<stem>.txt
    candidates.append('out_' + stem + '.txt')

    # проверяем существование рядом с progress файлом
    dirn = os.path.dirname(progress_file) or '.'
    for c in candidates:
        p = os.path.join(dirn, c)
        if os.path.exists(p):
            return p
    # если не нашли — вернём самый вероятный кандидат, чтобы в выводе было видно, что ожидалось
    return os.path.join(dirn, candidates[0]) if candidates else ''

def count_found_in_out(out_file: str) -> int:
    """
    Считает количество найденных адресов в out-файле.
    VanitySearch пишет найденные записи блоками, где строка начинается с 'PubAddress:'.
    """
    if not out_file or not os.path.exists(out_file):
        return -1
    cnt = 0
    try:
        with open(out_file, 'r', errors='ignore') as f:
            for line in f:
                if line.startswith('PubAddress:'):
                    cnt += 1
    except Exception:
        return -1
    return cnt

def parse_hex_to_int(hex_str):
    """Конвертирует hex строку в int"""
    if not hex_str:
        return None
    try:
        return int(hex_str, 16)
    except:
        return None

def _calc_key_at_percent(bit_range: int, percent: float) -> int:
    """
    Аналог SegmentSearch::CalculateKeyAtPercent + clamp.
    Для puzzle bits=N: полный диапазон [2^(N-1) .. 2^N - 1].
    percent задаётся в 0..100.
    """
    if bit_range <= 0:
        raise ValueError("bit_range must be > 0")
    # fullRangeStart = 2^(bits-1)
    start = 1 << (bit_range - 1)
    # fullRangeEnd = 2^bits - 1
    end = (1 << bit_range) - 1
    size = end - start + 1
    # integer math like in C++ (floor)
    offset = int(size * (percent / 100.0))
    k = start + offset
    if k < start:
        k = start
    if k > end:
        k = end
    return k


def parse_seg_file(seg_file: str, bit_range: int | None = None):
    """Парсит seg файл и возвращает словарь сегментов {name: (start, end, direction)}.

    Поддерживаемые форматы:
      - abs/dec/key: как раньше
      - pct/percent: проценты 0..100 (требует bit_range для вычисления abs-границ)
    """
    segments = {}
    if not os.path.exists(seg_file):
        return segments
    
    with open(seg_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Формат:
            #   abs <start_dec> <end_dec> <up|down> <name> [priority]
            #   key <start_hex> <end_hex> <up|down> <name> [priority]
            #   pct <startPercent> <endPercent> <up|down> <name> [priority]
            parts = line.split()
            if len(parts) >= 5 and parts[0] in ('abs', 'dec', 'key', 'pct', 'percent'):
                try:
                    # Для формата 'key' значения в hex (0x...), для 'abs'/'dec' - десятичные
                    if parts[0] == 'key':
                        # Убираем префикс 0x если есть
                        start_str = parts[1].replace('0x', '').replace('0X', '')
                        end_str = parts[2].replace('0x', '').replace('0X', '')
                        start = int(start_str, 16)
                        end = int(end_str, 16)
                    elif parts[0] in ('pct', 'percent'):
                        if bit_range is None or bit_range <= 0:
                            # Без bit_range невозможно корректно посчитать abs-границы.
                            # Вернём пусто — main() выведет понятную ошибку.
                            return {}
                        sp = float(parts[1])
                        ep = float(parts[2])
                        start = _calc_key_at_percent(bit_range, sp)
                        end = _calc_key_at_percent(bit_range, ep)
                    else:
                        start = int(parts[1])
                        end = int(parts[2])
                    direction = 0 if parts[3].lower() == 'up' else 1
                    name = parts[4]
                    segments[name] = (start, end, direction)
                except (ValueError, IndexError):
                    continue
    
    return segments

def parse_progress_file(progress_file):
    """Парсит progress файл и возвращает данные о прогрессе"""
    if not os.path.exists(progress_file):
        return None
    
    progress = {
        'totalKeysChecked': 0,
        'bitRange': 0,
        'startTime': 0,
        'lastSaveTime': 0,
        'targetAddress': '',
        'segments': []
    }
    
    current_seg = None
    in_segment = False
    
    with open(progress_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line == '---END---':
                continue
            
            if line == 'SEGMENT_START':
                in_segment = True
                current_seg = {}
                continue
            elif line == 'SEGMENT_END':
                if current_seg:
                    progress['segments'].append(current_seg)
                in_segment = False
                current_seg = None
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                
                if not in_segment:
                    if key == 'TotalKeysChecked':
                        progress['totalKeysChecked'] = int(value) if value.isdigit() else 0
                    elif key == 'BitRange':
                        progress['bitRange'] = int(value) if value.isdigit() else 0
                    elif key == 'StartTime':
                        progress['startTime'] = int(value) if value.isdigit() else 0
                    elif key == 'LastSaveTime':
                        progress['lastSaveTime'] = int(value) if value.isdigit() else 0
                    elif key == 'TargetAddress':
                        progress['targetAddress'] = value
                else:
                    if key == 'Name':
                        current_seg['name'] = value
                    elif key == 'RangeStart':
                        current_seg['rangeStart'] = value
                    elif key == 'RangeEnd':
                        current_seg['rangeEnd'] = value
                    elif key == 'CurrentKey':
                        current_seg['currentKey'] = value
                    elif key == 'Direction':
                        current_seg['direction'] = int(value) if value.isdigit() else 0
                    elif key == 'KeysChecked':
                        current_seg['keysChecked'] = int(value) if value.isdigit() else 0
                    elif key == 'Active':
                        current_seg['active'] = (value == '1')
                    elif key == 'RangeMode':
                        current_seg['rangeMode'] = int(value) if value.isdigit() else 0
    
    return progress

def calculate_segment_progress(seg_config, seg_progress):
    """Вычисляет прогресс сегмента в процентах и остаток"""
    name = seg_progress.get('name', '')
    if name not in seg_config:
        return None, None, None, None
    
    config_start, config_end, config_dir = seg_config[name]
    
    # Используем данные из progress файла (hex) если они есть, иначе из config (dec)
    range_start_hex = seg_progress.get('rangeStart', '')
    range_end_hex = seg_progress.get('rangeEnd', '')
    current_key_hex = seg_progress.get('currentKey', '')
    direction = seg_progress.get('direction', config_dir)
    
    # Конвертируем hex в int
    range_start = parse_hex_to_int(range_start_hex) if range_start_hex else config_start
    range_end = parse_hex_to_int(range_end_hex) if range_end_hex else config_end
    current_key = parse_hex_to_int(current_key_hex) if current_key_hex else None
    
    if current_key is None:
        return None, None, None, None
    
    # Вычисляем размер сегмента
    if direction == 0:  # UP
        seg_size = range_end - range_start
        progress = current_key - range_start
        remaining = range_end - current_key
    else:  # DOWN
        seg_size = range_start - range_end
        progress = range_start - current_key
        remaining = current_key - range_end
    
    if seg_size <= 0:
        return None, None, None, None
    
    percent = (progress / seg_size) * 100.0 if seg_size > 0 else 0.0
    percent = max(0.0, min(100.0, percent))  # Clamp to [0, 100]
    
    return percent, progress, remaining, seg_size

def format_number(num):
    """Форматирует большое число в читаемый вид"""
    if num is None:
        return "N/A"
    if num < 1000:
        return str(num)
    elif num < 1_000_000:
        return f"{num/1000:.2f}K"
    elif num < 1_000_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num < 1_000_000_000_000:
        return f"{num/1_000_000_000:.2f}G"
    else:
        return f"{num/1_000_000_000_000:.2f}T"

def format_time(ts):
    """Форматирует timestamp"""
    if ts <= 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def main():
    seg_file = sys.argv[1] if len(sys.argv) > 1 else 'seg_gpu_range.txt'
    progress_file = sys.argv[2] if len(sys.argv) > 2 else 'progress_gpu_range.dat'
    out_file = sys.argv[3] if len(sys.argv) > 3 else ''
    if not out_file:
        out_file = infer_out_file(progress_file)

    # Парсим прогресс (раньше конфиг читался первым, но для pct-сегментов нужен BitRange из прогресса)
    progress = parse_progress_file(progress_file)
    if not progress:
        print(f"Ошибка: не удалось загрузить прогресс из {progress_file}")
        print("Убедитесь что поиск запущен с параметром -progress")
        sys.exit(1)

    # Парсим конфигурацию сегментов
    seg_config = parse_seg_file(seg_file, bit_range=progress.get('bitRange', 0))
    if not seg_config:
        print(f"Ошибка: не удалось загрузить конфигурацию из {seg_file}")
        print("Примечание: для pct/percent сегментов нужен BitRange из progress-файла.")
        sys.exit(1)
    
    # Заголовок
    print("=" * 120)
    print(f"Прогресс поиска")
    print("=" * 120)
    print(f"Файл конфигурации: {seg_file}")
    print(f"Файл прогресса:    {progress_file}")
    print(f"Битовый диапазон:  {progress['bitRange']}")
    print(f"Целевой адрес:     {progress['targetAddress']}")
    # Найдено (по out-файлу, если он задан или удалось угадать)
    found_cnt = count_found_in_out(out_file)
    if found_cnt >= 0:
        print(f"Найдено:           {found_cnt} (из {os.path.basename(out_file)})")
    else:
        if out_file:
            print(f"Найдено:           N/A (не найден out-файл: {os.path.basename(out_file)})")
        else:
            print("Найдено:           N/A (out-файл не указан)")
    print(f"Всего проверено:   {format_number(progress['totalKeysChecked'])} ключей")
    if progress['startTime'] > 0:
        print(f"Начало поиска:     {format_time(progress['startTime'])}")
    if progress['lastSaveTime'] > 0:
        print(f"Последнее сохранение: {format_time(progress['lastSaveTime'])}")
    print("=" * 120)
    print()
    
    # Заголовок таблицы
    print(f"{'Сегмент':<18} {'Статус':<6} {'Прогресс %':<12} {'Проверено':<18} {'Осталось':<18} {'Размер':<18} {'Ключей':<18}")
    print("-" * 120)
    
    # Прогресс по сегментам
    total_checked = 0
    active_count = 0
    completed_count = 0
    
    for seg_progress in progress['segments']:
        name = seg_progress.get('name', 'unknown')
        active = seg_progress.get('active', False)
        keys_checked = seg_progress.get('keysChecked', 0)
        
        if active:
            active_count += 1
        else:
            completed_count += 1
        
        total_checked += keys_checked
        
        # Вычисляем прогресс
        percent, progress_val, remaining, seg_size = calculate_segment_progress(seg_config, seg_progress)
        
        # Важно: на Windows при выводе в pipe/Powershell кодировка часто cp1251,
        # и некоторые Unicode символы (например '▶') не кодируются => UnicodeEncodeError.
        # Поэтому используем только ASCII.
        status = "DONE" if not active else "RUN"
        
        if percent is not None:
            progress_str = f"{percent:.2f}%"
            progress_num_str = format_number(progress_val)
            remaining_str = format_number(remaining)
            size_str = format_number(seg_size)
        else:
            progress_str = "N/A"
            progress_num_str = "N/A"
            remaining_str = "N/A"
            size_str = "N/A"
        
        keys_str = format_number(keys_checked)
        
        print(f"{name:<18} {status:<6} {progress_str:>12} {progress_num_str:>18} {remaining_str:>18} {size_str:>18} {keys_str:>18}")
    
    print("-" * 120)
    print(f"Всего сегментов: {len(progress['segments'])} | Активных: {active_count} | Завершено: {completed_count}")
    print(f"Всего проверено ключей (сумма по сегментам): {format_number(total_checked)}")
    print()

if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        # head/tail закрыли пайп — это нормально
        try:
            sys.stdout.close()
        except Exception:
            pass
        sys.exit(0)

