# 🚀 Быстрый старт GUI

## Запуск GUI

### Графический режим (Tkinter):
```bash
python3 vanity_gui_unified.py
```

### CLI режим:
```bash
python3 vanity_gui_unified.py --cli
```

---

## Пример использования GUI

### 1. Компиляция (если нужно)

**CPU режим (macOS/Linux):**
- Нажать кнопку `BUILD/REBUILD`
- Backend: CPU
- Подождать завершения компиляции

**GPU режим (если есть CUDA):**
- Нажать кнопку `BUILD/REBUILD`
- Backend: GPU
- CCAP: 8.9 (или ваша версия)
- Подождать завершения компиляции

### 2. Настройка параметров

**Обязательные:**
- **Segment source file:** `seg_test_cpu_db.txt` (или ваш файл)
- **Patterns:** `1TEST` (или ваш паттерн)
- **Bits:** `71` (битовый диапазон)
- **Threads (-t):** `8` (количество потоков)

**Опциональные:**
- **База данных:** `bitcoin_addresses_optimized.sqlite` (если нужна проверка)
- **Max found (-m):** `5` (максимальное количество найденных)
- **Autosave:** `300` (автосохранение каждые 300 сек)

**GPU параметры (только для GPU режима):**
- **GPU ID:** `0` (ID вашей видеокарты)
- **Grid (-g):** `64,128` (размер сетки)

### 3. Запуск

- Нажать кнопку `START`
- В логе появится:
  ```
  [START] groups=1 backend=CPU workdir=/Users/.../runs
  [START] ℹ️  Load Balancer: Автоматически включён для равномерного распределения 8 потоков по сегментам
  [START Group 1] 📁 База данных: bitcoin_addresses_optimized.sqlite
  [START Group 1] PID=12345
  ```

### 4. Мониторинг

- **Progress:** Показать текущий прогресс
- **Tail log:** Показать последние строки лога
- **Показать найденные:** Результаты поиска (по паттерну)
- **🎯 Найдено из базы:** Результаты проверки базы данных

### 5. Остановка

- **STOP:** Остановить текущие поиски
- **STOP ALL:** Остановить все процессы VanitySearch

---

## Пример использования CLI

```bash
python3 vanity_gui_unified.py --cli
```

**Диалог:**
```
Commands: start stop tail progress found rebuild clear exit
> start

Base name [run]: test_search
Path to seg file (source) []: seg_test_cpu_db.txt
bits [71]: 71
threads (-t) [8]: 8
autosave (sec) [300]: 300
maxFound (-m) [5]: 5
backend (cpu/gpu) [cpu]: cpu
Database path (leave empty to skip) []: bitcoin_addresses_optimized.sqlite
pattern (single) []: 1TEST

[START] PID=12345
[START] ℹ️  Load Balancer: Автоматически включён для 8 потоков
[START] 📁 Database: bitcoin_addresses_optimized.sqlite
[CMD] ./VanitySearch -seg test_search_seg.txt -bits 71 -db bitcoin_addresses_optimized.sqlite -t 8 -m 5 -progress test_search_progress.dat -autosave 300 -o test_search_out.txt 1TEST
```

**Проверить прогресс:**
```
> progress
```

**Остановить:**
```
> stop
```

**Показать лог:**
```
> tail
```

---

## Структура файлов

Все файлы сохраняются в `runs/` директории:

```
runs/
├── run_seg.txt              # Файл с сегментами
├── run_progress.dat         # Файл прогресса (для resume)
├── run_out.txt              # Найденные адреса (по паттерну)
├── run_DatabaseFound.txt    # Найденные адреса (из базы)
├── run.log                  # Полный лог поиска
└── run.pid                  # PID процесса
```

---

## Load Balancer

**Работает автоматически!**

- Равномерно распределяет потоки по сегментам
- Динамически переназначает потоки на новые сегменты
- Ребалансировка каждые 60 секунд
- **Никаких дополнительных параметров не требуется**

**Пример:**
```
12 сегментов, 8 потоков:
┌─────────┬──────────┬──────────┬──────────┐
│ Thread 0│ Thread 1 │ Thread 2 │ Thread 3 │
│ Seg #1  │ Seg #2   │ Seg #3   │ Seg #4   │
└─────────┴──────────┴──────────┴──────────┘
┌─────────┬──────────┬──────────┬──────────┐
│ Thread 4│ Thread 5 │ Thread 6 │ Thread 7 │
│ Seg #5  │ Seg #6   │ Seg #7   │ Seg #8   │
└─────────┴──────────┴──────────┴──────────┘

Когда Thread 0 завершает Seg #1:
  → Переключается на Seg #9
Когда Thread 1 завершает Seg #2:
  → Переключается на Seg #10
...
```

---

## База данных

**Формат:** SQLite (.sqlite, .sqlite3, .db)

**Как работает:**
1. Загружается в RAM при старте (12M адресов → 6 сек)
2. Bloom Filter для быстрой проверки
3. Все сгенерированные адреса проверяются **ДО** проверки паттерна
4. Результаты сохраняются в `*_DatabaseFound.txt`

**Пример:**
```
Сгенерирован адрес: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
  ↓
Bloom Filter: Возможно в базе
  ↓
Hash160 lookup: ✅ НАЙДЕНО!
  ↓
Сохранить в *_DatabaseFound.txt

Паттерн не проверяется - адрес уже найден в базе!
```

---

## Полезные команды

### Посмотреть последние найденные адреса:
```bash
tail -f runs/run_DatabaseFound.txt
```

### Посмотреть лог в реальном времени:
```bash
tail -f runs/run.log
```

### Остановить все процессы VanitySearch:
```bash
pkill -f VanitySearch
```

### Проверить прогресс:
```bash
python3 show_segment_progress.py runs/run_progress.dat
```

---

## Типичные проблемы

### 1. "Бинарник VanitySearch не найден"
**Решение:** Нажать `BUILD/REBUILD` или указать путь в `Binary override`

### 2. "Permission denied"
**Решение:**
```bash
chmod +x VanitySearch
```

### 3. GUI не запускается (No module named 'tkinter')
**Решение:** Использовать CLI режим:
```bash
python3 vanity_gui_unified.py --cli
```

### 4. База данных не загружается
**Проверить:**
- Файл существует
- Формат SQLite
- Таблица `bitcoin_addresses` с колонкой `address`

---

## Оптимизация производительности

### CPU режим:
- Количество потоков = количество ядер CPU
- Для Ryzen 9 5950X: `-t 32`
- Для M1 Max: `-t 10`

### GPU режим (CUDA):
- Grid size зависит от видеокарты
- RTX 3090: `-g 128,256`
- RTX 4090: `-g 256,512`

### База данных:
- 12M адресов: ~2GB RAM, 6 сек загрузка
- Bloom Filter: 0.1% false positive rate
- Скорость: ~8-10 Mkey/s (CPU)

---

## Документация

- **GUI_VERIFICATION_REPORT.md** - Полный отчёт о проверке GUI
- **TEST_GUI.md** - Чеклист тестирования
- **OPTIMIZATION_RESULTS.md** - Результаты оптимизаций
- **GUI_DATABASE_INTEGRATION.md** - Интеграция базы данных

---

**Дата:** 5 января 2026  
**Версия:** v1.0  
**Автор:** VanitySearch GUI Unified

