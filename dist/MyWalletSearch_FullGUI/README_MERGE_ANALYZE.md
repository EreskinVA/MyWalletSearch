# Объединение и анализ out* файлов

## Описание

Два скрипта для работы с результатами VanitySearch:

1. **merge_out_files.py** - объединяет все out* файлы в один нормализованный файл
2. **analyze_merged.py** - анализирует объединённый файл (аналог analyze_seg_74_5_76.py)

## Использование

### Шаг 1: Объединение файлов

```bash
python3 merge_out_files.py --output merged_out_all.txt
```

Опции:
- `--base-dir DIR` - базовая директория для поиска (по умолчанию: текущая)
- `--output FILE` - имя выходного файла (по умолчанию: merged_out_all.txt)
- `--no-dedup` - не удалять дубликаты по адресу
- `--min-fields N` - минимальное число полей для записи (по умолчанию: 2)

Скрипт:
- Находит все out* файлы в проекте (включая подпапки)
- Парсит их с учётом разных форматов
- Вычисляет недостающие поля из имеющихся данных:
  - Priv (DEC) из Priv (HEX) и наоборот
  - PuzzleKeyAbs из PuzzleStart + PuzzlePos0
  - PuzzlePos0 из PuzzleKeyAbs - PuzzleStart
  - SegKey из PuzzleKeyAbs если нет
  - И другие зависимости
- Объединяет в один файл с единым форматом
- Удаляет дубликаты по адресу (опционально)

### Шаг 2: Анализ объединённого файла

```bash
python3 analyze_merged.py --input merged_out_all.txt --target "1PWo3JeB6XZSP1pv3i7nWmDpZcE5ambSMJ" --puzzle-bits 71
```

Опции:
- `--input FILE` - путь к объединённому файлу (по умолчанию: merged_out_all.txt)
- `--target ADDRESS` - целевой адрес для анализа
- `--prefix PREFIX` - целевой префикс (если не указан, берётся из target)
- `--puzzle-bits N` - bits для PuzzleKeyAbs (по умолчанию: 71, или 'off')
- `--max-records N` - ограничить число записей для анализа
- `--suggest N` - сколько паттернов предложить (по умолчанию: 24)
- `--verify-crypto N` - крипто-проверка: 0=off, N=first N, all=all
- `--out FILE` - сохранить отчёт в файл

## Примеры

### Полное объединение и анализ

```bash
# 1. Объединить все файлы
python3 merge_out_files.py --output merged_out_all.txt

# 2. Проанализировать с целевым адресом
python3 analyze_merged.py \
    --input merged_out_all.txt \
    --target "1PWo3JeB6XZSP1pv3i7nWmDpZcE5ambSMJ" \
    --puzzle-bits 71 \
    --out analysis_report.txt
```

### Быстрый анализ первых 1000 записей

```bash
python3 analyze_merged.py \
    --input merged_out_all.txt \
    --target "1PWo3JeB6XZSP1pv3i7nWmDpZcE5ambSMJ" \
    --max-records 1000 \
    --puzzle-bits 71
```

## Вычисляемые поля

Скрипт `merge_out_files.py` автоматически вычисляет недостающие поля:

- **Priv (DEC)** ← из Priv (HEX)
- **Priv (HEX)** ← из Priv (DEC)
- **PuzzleKeyAbs (DEC)** ← из PuzzleStart + PuzzlePos0
- **PuzzleKeyAbs (HEX)** ← из PuzzleKeyAbs (DEC)
- **PuzzlePos0** ← из PuzzleKeyAbs - PuzzleStart
- **SegKey** ← из PuzzleKeyAbs (если нет)
- И другие зависимости

## Формат выходного файла

Объединённый файл имеет единый формат:

```
PubAddress: 1PWo3Je...
Priv (WIF): ...
Priv (HEX): 0x...
Priv (DEC): ...
PuzzleBits: 71
PuzzleStart (DEC): ...
PuzzlePos0 (DEC): ...
PuzzleKeyAbs (HEX): 0x...
PuzzleKeyAbs (DEC): ...
SegKey (HEX): 0x...
SegKey (DEC): ...
Segment: ...
SegmentDir: UP
SegmentOffset (DEC): ...
SegmentSize (DEC): ...

```

## Отличия от analyze_seg_74_5_76.py

- Работает с одним файлом вместо glob паттерна
- Использует `--input` вместо `--base-dir` и `--glob`
- Все остальные функции идентичны

