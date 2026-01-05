#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для объединения всех out* файлов в один нормализованный файл.

Назначение:
- Находит все out* файлы в проекте
- Парсит их с учётом разных форматов
- Вычисляет недостающие поля из имеющихся данных
- Объединяет в один файл с единым форматом
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

# Segment names в out файлах могут содержать суффикс типа "name (#5)". Нормализуем.
_SEG_SUFFIX_RE = re.compile(r"\s*\(#\d+\)\s*$")


def _safe_int(x: str) -> Optional[int]:
    """Безопасное преобразование строки в int."""
    try:
        s = str(x).strip()
        if s.startswith("0x") or s.startswith("0X"):
            return int(s, 16)
        return int(s)
    except Exception:
        return None


def _hex_to_dec(hex_str: str) -> Optional[str]:
    """Преобразует HEX в DEC строку."""
    val = _safe_int(hex_str)
    return str(val) if val is not None else None


def _dec_to_hex(dec_str: str) -> Optional[str]:
    """Преобразует DEC в HEX строку (с префиксом 0x)."""
    val = _safe_int(dec_str)
    return f"0x{val:X}" if val is not None else None


def _normalize_wif(wif: str) -> str:
    """Убирает префикс p2pkh: если есть."""
    wif = wif.strip()
    if wif.startswith("p2pkh:"):
        return wif[6:].strip()
    return wif


def parse_result_file(filepath: Path) -> list[dict[str, str]]:
    """Парсит out-файл VanitySearch, собирая блоки по 'PubAddress:'."""
    results: list[dict[str, str]] = []
    current: dict[str, str] = {}

    with filepath.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("PubAddress:"):
                if current:
                    results.append(current)
                current = {"file": filepath.name}
                current["address"] = line.split(":", 1)[1].strip()
                continue

            if ":" not in line:
                continue

            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()

            if k == "Priv (HEX)":
                current["priv_hex"] = v
            elif k == "Priv (DEC)":
                current["priv_dec"] = v
            elif k == "Priv (WIF)":
                current["priv_wif"] = _normalize_wif(v)
            elif k == "PuzzlePos0 (DEC)":
                current["puzzle_pos0"] = v
            elif k == "PuzzleBits":
                current["puzzle_bits"] = v
            elif k == "PuzzleStart (DEC)":
                current["puzzle_start_dec"] = v
            elif k == "PuzzleKeyAbs (HEX)":
                current["puzzle_key_abs_hex"] = v
            elif k == "PuzzleKeyAbs (DEC)":
                current["puzzle_key_abs"] = v
            elif k == "SegKey (HEX)":
                current["seg_key_hex"] = v
            elif k == "SegKey (DEC)":
                current["seg_key"] = v
            elif k == "Segment":
                current["segment"] = _SEG_SUFFIX_RE.sub("", v).strip()
            elif k == "SegmentDir":
                current["segment_dir"] = v
            elif k == "SegmentOffset (DEC)":
                current["segment_offset"] = v
            elif k == "SegmentSize (DEC)":
                current["segment_size"] = v

    if current:
        results.append(current)
    return results


def compute_missing_fields(record: dict[str, str]) -> dict[str, str]:
    """
    Вычисляет недостающие поля из имеющихся данных.
    
    Правила вычисления:
    - Priv (DEC) из Priv (HEX) если нет
    - Priv (HEX) из Priv (DEC) если нет
    - PuzzleKeyAbs (DEC) из Priv (DEC) если нет и нет других указаний
    - PuzzleKeyAbs (HEX) из PuzzleKeyAbs (DEC) если нет
    - PuzzleKeyAbs (DEC) из PuzzleStart + PuzzlePos0 если есть оба
    - PuzzlePos0 из PuzzleKeyAbs - PuzzleStart если есть оба
    - SegKey из PuzzleKeyAbs если нет
    """
    result = record.copy()

    # Priv (DEC) из Priv (HEX)
    if "priv_dec" not in result and "priv_hex" in result:
        dec = _hex_to_dec(result["priv_hex"])
        if dec:
            result["priv_dec"] = dec

    # Priv (HEX) из Priv (DEC)
    if "priv_hex" not in result and "priv_dec" in result:
        hex_val = _dec_to_hex(result["priv_dec"])
        if hex_val:
            result["priv_hex"] = hex_val

    # PuzzleKeyAbs (DEC) из PuzzleStart + PuzzlePos0
    if "puzzle_key_abs" not in result:
        if "puzzle_start_dec" in result and "puzzle_pos0" in result:
            start = _safe_int(result["puzzle_start_dec"])
            pos0 = _safe_int(result["puzzle_pos0"])
            if start is not None and pos0 is not None:
                result["puzzle_key_abs"] = str(start + pos0)

    # PuzzlePos0 из PuzzleKeyAbs - PuzzleStart
    if "puzzle_pos0" not in result:
        if "puzzle_key_abs" in result and "puzzle_start_dec" in result:
            abs_val = _safe_int(result["puzzle_key_abs"])
            start = _safe_int(result["puzzle_start_dec"])
            if abs_val is not None and start is not None:
                result["puzzle_pos0"] = str(abs_val - start)

    # PuzzleKeyAbs (DEC) из Priv (DEC) если нет (fallback)
    if "puzzle_key_abs" not in result and "priv_dec" in result:
        priv_dec = _safe_int(result["priv_dec"])
        if priv_dec is not None:
            result["puzzle_key_abs"] = str(priv_dec)

    # PuzzleKeyAbs (HEX) из PuzzleKeyAbs (DEC)
    if "puzzle_key_abs_hex" not in result and "puzzle_key_abs" in result:
        hex_val = _dec_to_hex(result["puzzle_key_abs"])
        if hex_val:
            result["puzzle_key_abs_hex"] = hex_val

    # PuzzleKeyAbs (DEC) из PuzzleKeyAbs (HEX)
    if "puzzle_key_abs" not in result and "puzzle_key_abs_hex" in result:
        dec = _hex_to_dec(result["puzzle_key_abs_hex"])
        if dec:
            result["puzzle_key_abs"] = str(dec)

    # SegKey из PuzzleKeyAbs если нет
    if "seg_key" not in result and "puzzle_key_abs" in result:
        result["seg_key"] = result["puzzle_key_abs"]

    if "seg_key_hex" not in result and "seg_key" in result:
        hex_val = _dec_to_hex(result["seg_key"])
        if hex_val:
            result["seg_key_hex"] = hex_val

    if "seg_key" not in result and "seg_key_hex" in result:
        dec = _hex_to_dec(result["seg_key_hex"])
        if dec:
            result["seg_key"] = str(dec)

    return result


def find_all_out_files(base_dir: Path) -> list[Path]:
    """Находит все out* файлы в проекте."""
    files: list[Path] = []
    
    # Ищем в корне и подпапках
    patterns = ["out*.txt", "**/out*.txt"]
    for pattern in patterns:
        files.extend(base_dir.glob(pattern))
    
    # Убираем дубликаты и сортируем
    files = sorted(set(files))
    return files


def merge_out_files(
    base_dir: Path,
    output_file: Path,
    *,
    deduplicate: bool = True,
    min_fields: int = 2,
) -> dict[str, Any]:
    """
    Объединяет все out* файлы в один нормализованный файл.
    
    Args:
        base_dir: Базовая директория для поиска файлов
        output_file: Путь к выходному файлу
        deduplicate: Удалять ли дубликаты по адресу
        min_fields: Минимальное число полей для записи (кроме address и file)
    
    Returns:
        Статистика обработки
    """
    files = find_all_out_files(base_dir)
    
    all_records: list[dict[str, str]] = []
    file_stats: dict[str, int] = {}
    seen_addresses: set[str] = set()
    
    for filepath in files:
        try:
            records = parse_result_file(filepath)
            file_stats[filepath.name] = len(records)
            
            for record in records:
                # Вычисляем недостающие поля
                normalized = compute_missing_fields(record)
                
                # Проверяем минимальные требования
                fields_count = sum(1 for k, v in normalized.items() if k not in ("address", "file") and v)
                if fields_count < min_fields:
                    continue
                
                # Дедупликация по адресу
                addr = normalized.get("address", "")
                if deduplicate and addr:
                    if addr in seen_addresses:
                        continue
                    seen_addresses.add(addr)
                
                all_records.append(normalized)
        except Exception as e:
            print(f"Ошибка при обработке {filepath}: {e}")
            continue
    
    # Записываем объединённый файл
    with output_file.open("w", encoding="utf-8") as f:
        for record in all_records:
            f.write(f"PubAddress: {record.get('address', '')}\n")
            
            if record.get("priv_wif"):
                f.write(f"Priv (WIF): {record['priv_wif']}\n")
            if record.get("priv_hex"):
                f.write(f"Priv (HEX): {record['priv_hex']}\n")
            if record.get("priv_dec"):
                f.write(f"Priv (DEC): {record['priv_dec']}\n")
            
            if record.get("puzzle_bits"):
                f.write(f"PuzzleBits: {record['puzzle_bits']}\n")
            if record.get("puzzle_start_dec"):
                f.write(f"PuzzleStart (DEC): {record['puzzle_start_dec']}\n")
            if record.get("puzzle_pos0"):
                f.write(f"PuzzlePos0 (DEC): {record['puzzle_pos0']}\n")
            if record.get("puzzle_key_abs_hex"):
                f.write(f"PuzzleKeyAbs (HEX): {record['puzzle_key_abs_hex']}\n")
            if record.get("puzzle_key_abs"):
                f.write(f"PuzzleKeyAbs (DEC): {record['puzzle_key_abs']}\n")
            
            if record.get("seg_key_hex"):
                f.write(f"SegKey (HEX): {record['seg_key_hex']}\n")
            if record.get("seg_key"):
                f.write(f"SegKey (DEC): {record['seg_key']}\n")
            
            if record.get("segment"):
                f.write(f"Segment: {record['segment']}\n")
            if record.get("segment_dir"):
                f.write(f"SegmentDir: {record['segment_dir']}\n")
            if record.get("segment_offset"):
                f.write(f"SegmentOffset (DEC): {record['segment_offset']}\n")
            if record.get("segment_size"):
                f.write(f"SegmentSize (DEC): {record['segment_size']}\n")
            
            f.write("\n")
    
    return {
        "files_processed": len(files),
        "records_total": len(all_records),
        "file_stats": file_stats,
        "output_file": str(output_file),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Объединение всех out* файлов в один нормализованный файл")
    parser.add_argument(
        "--base-dir",
        default=str(Path(__file__).parent),
        help="Базовая директория для поиска out* файлов",
    )
    parser.add_argument(
        "--output",
        default="merged_out_all.txt",
        help="Имя выходного файла",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Не удалять дубликаты по адресу",
    )
    parser.add_argument(
        "--min-fields",
        type=int,
        default=2,
        help="Минимальное число полей (кроме address и file) для записи",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).expanduser().resolve()
    output_file = base_dir / args.output
    
    print(f"Поиск out* файлов в {base_dir}...")
    stats = merge_out_files(
        base_dir,
        output_file,
        deduplicate=not args.no_dedup,
        min_fields=args.min_fields,
    )
    
    print(f"\nОбработано файлов: {stats['files_processed']}")
    print(f"Всего записей: {stats['records_total']}")
    print(f"Выходной файл: {stats['output_file']}")
    
    if stats['file_stats']:
        print("\nСтатистика по файлам (топ-10):")
        for name, count in sorted(stats['file_stats'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {name}: {count}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

