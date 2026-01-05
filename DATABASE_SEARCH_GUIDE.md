# Руководство по поиску адресов из базы данных

## Обзор

VanitySearch теперь поддерживает проверку сгенерированных Bitcoin-адресов против базы данных SQLite. Если сгенерированный адрес найден в базе данных, соответствующий приватный ключ автоматически сохраняется.

## Подготовка базы данных

### Шаг 1: Конвертация LMDB → SQLite

Если у вас есть база данных LMDB (например, `bitcoin_addresses.db`), сначала конвертируйте её в оптимизированную SQLite базу:

```bash
cd VanitySearch
python3 convert_lmdb_to_sqlite.py \
  --input /path/to/bitcoin_addresses.db \
  --output bitcoin_addresses_optimized.sqlite \
  --test \
  --yes
```

**Параметры:**
- `--input` - путь к LMDB базе (по умолчанию: `/Users/vladimirereskin/Projects/BitcoinSearch/bitcoin_addresses.db`)
- `--output` - путь для SQLite базы (по умолчанию: `bitcoin_addresses_optimized.sqlite`)
- `--test` - запустить тест производительности после конвертации
- `--yes` - автоматическое подтверждение (без запроса)

**Результат конвертации:**
- ✅ Размер уменьшен с ~10 GB до ~3.2 GB (экономия 68%)
- ✅ Скорость поиска: ~6 микросекунд на адрес
- ✅ Производительность: ~157,000 проверок/сек

### Шаг 2: Проверка базы данных

После конвертации проверьте размер и структуру базы:

```bash
ls -lh bitcoin_addresses_optimized.sqlite
sqlite3 bitcoin_addresses_optimized.sqlite "SELECT COUNT(*) FROM addresses;"
```

## Использование

### Основной синтаксис

```bash
./VanitySearch [опции] -db <путь_к_базе_данных> [префикс]
```

### Примеры использования

#### Пример 1: Поиск только в базе данных (без префикса)

```bash
./VanitySearch -db bitcoin_addresses_optimized.sqlite -t 8
```

Эта команда будет:
- Генерировать случайные Bitcoin-адреса
- Проверять каждый адрес против базы данных
- Сохранять найденные совпадения в `DatabaseFound.txt`

#### Пример 2: Поиск префикса + проверка базы данных

```bash
./VanitySearch -db bitcoin_addresses_optimized.sqlite -t 8 1Bitcoin
```

Эта команда будет:
- Искать адреса с префиксом "1Bitcoin"
- **Дополнительно** проверять **все** сгенерированные адреса против базы данных
- Сохранять результаты:
  - Префиксные совпадения → `Result.txt` (или файл из `-o`)
  - Совпадения из базы → `Result_DatabaseFound.txt`

#### Пример 3: GPU поиск с проверкой базы данных

```bash
./VanitySearch -gpu -db bitcoin_addresses_optimized.sqlite -t 4 -o MyResults.txt 1Test
```

#### Пример 4: Segment search с проверкой базы данных

```bash
./VanitySearch \
  -db bitcoin_addresses_optimized.sqlite \
  -seg segments_puzzle71.txt \
  -bits 71 \
  -progress progress_71.dat \
  -autosave 300 \
  -t 8
```

## Параметры командной строки

### Новый параметр

- **`-db <путь>`** - путь к SQLite базе данных для проверки адресов
  - Пример: `-db bitcoin_addresses_optimized.sqlite`
  - База должна содержать таблицу `addresses` с колонкой `address`

### Совместимость с другими опциями

Опция `-db` совместима со всеми существующими опциями:
- ✅ `-gpu` - GPU ускорение
- ✅ `-t` - количество CPU потоков
- ✅ `-seg` - segment search
- ✅ `-bits` - bit range для puzzle
- ✅ `-progress` / `-resume` - сохранение/восстановление прогресса
- ✅ `-i` - файл с префиксами
- ✅ `-o` - выходной файл
- ✅ Wildcards (`*`, `?`)

## Формат выходных файлов

### Файл с находками из базы данных

Имя файла: `<output_file>_DatabaseFound.txt` или `DatabaseFound.txt` (если `-o` не указан)

Пример содержимого:

```
=================================================================
🎯 НАЙДЕН АДРЕС ИЗ БАЗЫ ДАННЫХ!
=================================================================
PubAddress: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Priv (WIF): p2pkh:5HpHagT65TZzG1PH3CSu63k8DbpvD8s5ip4nEB3kEsreAnchuDf
Priv (HEX): 0x0000000000000000000000000000000000000000000000000000000000000001
Priv (DEC): 1
=================================================================

=================================================================
🎯 НАЙДЕН АДРЕС ИЗ БАЗЫ ДАННЫХ!
=================================================================
PubAddress: 1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH
Priv (WIF): p2pkh:5J64pq77XjeacCezwmAr2V1s7snvvJkuAz8sENxw7xCkikceV6e
Priv (HEX): 0x0000000000000000000000000000000000000000000000000000000000000002
Priv (DEC): 2
=================================================================
```

### Консольный вывод

При инициализации:

```
[Database] Инициализация проверки базы данных...
[Database] Открываем SQLite базу: bitcoin_addresses_optimized.sqlite
[Database] Адресов в базе: 23,299,529
[Database] ✅ База данных готова к проверке
[Database]    Путь: bitcoin_addresses_optimized.sqlite
[Database]    Результаты будут сохранены в: DatabaseFound.txt
```

При нахождении адреса:

```
=================================================================
🎯 НАЙДЕН АДРЕС ИЗ БАЗЫ ДАННЫХ!
=================================================================
PubAddress: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Priv (HEX): 0x0000000000000000000000000000000000000000000000000000000000000001
Priv (DEC): 1
Сохранено в: DatabaseFound.txt
=================================================================
```

При завершении поиска:

```
[Database] Всего найдено адресов из базы: 5
[Database] Результаты сохранены в: DatabaseFound.txt
```

## Производительность

### Влияние на скорость поиска

- **CPU режим:** ~5-10% снижение скорости (из-за проверки базы данных)
- **GPU режим:** ~1-2% снижение скорости (база проверяется на CPU параллельно)
- **Segment search:** минимальное влияние

### Оптимизация

База данных SQLite с индексом обеспечивает:
- ⚡ O(log n) поиск
- 💾 Минимальное потребление RAM
- 🚀 ~157,000 проверок/секунду

## Структура базы данных

### Требования к базе

База данных должна быть SQLite с таблицей `addresses`:

```sql
CREATE TABLE addresses (
    address TEXT PRIMARY KEY NOT NULL
);

CREATE INDEX idx_address ON addresses(address);
```

### Создание собственной базы

Если у вас есть текстовый файл с адресами:

```python
import sqlite3

# Создаем базу
conn = sqlite3.connect('my_addresses.sqlite')
cursor = conn.cursor()

# Создаем таблицу
cursor.execute('''
    CREATE TABLE IF NOT EXISTS addresses (
        address TEXT PRIMARY KEY NOT NULL
    )
''')

# Читаем адреса из файла
with open('addresses.txt', 'r') as f:
    for line in f:
        address = line.strip()
        if address:
            cursor.execute('INSERT OR IGNORE INTO addresses (address) VALUES (?)', (address,))

# Создаем индекс
cursor.execute('CREATE INDEX IF NOT EXISTS idx_address ON addresses(address)')

# Оптимизируем
cursor.execute('VACUUM')
cursor.execute('ANALYZE')

conn.commit()
conn.close()
```

## Устранение неполадок

### Ошибка: "Cannot open database file"

```bash
# Проверьте путь к базе
ls -l bitcoin_addresses_optimized.sqlite

# Проверьте права доступа
chmod 644 bitcoin_addresses_optimized.sqlite
```

### Ошибка: "Table 'addresses' not found"

База данных имеет неправильную структуру. Убедитесь, что таблица создана правильно:

```bash
sqlite3 bitcoin_addresses_optimized.sqlite "SELECT name FROM sqlite_master WHERE type='table';"
```

### Медленная проверка

Убедитесь, что создан индекс:

```bash
sqlite3 bitcoin_addresses_optimized.sqlite "SELECT name FROM sqlite_master WHERE type='index';"
```

Должен присутствовать индекс `idx_address`.

## Компиляция

При компиляции VanitySearch теперь требуется линковка с SQLite:

### Linux / macOS

```bash
# Установить SQLite (если не установлен)
# Ubuntu/Debian:
sudo apt-get install libsqlite3-dev

# macOS:
brew install sqlite3

# Компиляция
make
```

В `Makefile` должна быть строка:

```makefile
LFLAGS = ... -lsqlite3
```

### Windows (MSVC)

Добавьте в проект:
- Include path: путь к `sqlite3.h`
- Library: `sqlite3.lib`

## Дополнительные примеры

### Проверка 10 миллионов адресов

```bash
# Генерируем 10M адресов с проверкой базы
./VanitySearch -db bitcoin_addresses_optimized.sqlite -t 16 -m 10000000
```

### Поиск wildcards + проверка базы

```bash
./VanitySearch -db bitcoin_addresses_optimized.sqlite "1Test*" -t 8
```

### Мультипаттерн поиск + база

```bash
# Создаем файл patterns.txt:
# 1Bitcoin
# 1Test
# 1Love

./VanitySearch -db bitcoin_addresses_optimized.sqlite -i patterns.txt -t 8
```

## Примечания

1. ✅ Проверка базы данных **не отменяет** обычный поиск префиксов/паттернов
2. ✅ Адрес может совпадать **одновременно** с префиксом И быть в базе
3. ✅ Результаты сохраняются в **разные файлы**:
   - Префиксные совпадения → обычный output файл
   - Совпадения из базы → `*_DatabaseFound.txt`
4. ✅ Дедупликация: повторные находки одного адреса не записываются
5. ✅ Потокобезопасность: многопоточный доступ к базе защищен

## Лицензия

Интеграция базы данных сохраняет лицензию VanitySearch (GPL v3).

## Автор

Интеграция SQLite базы данных добавлена в 2026 году.

