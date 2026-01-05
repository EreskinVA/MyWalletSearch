# Компиляция VanitySearch с поддержкой базы данных

## Требования

- SQLite3 библиотека и заголовочные файлы
- Компилятор: GCC, Clang или MSVC
- Make (для Linux/macOS)

## Установка SQLite3

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install libsqlite3-dev
```

### macOS

```bash
# Homebrew
brew install sqlite3

# Или использовать системный SQLite (уже установлен)
```

### CentOS/RHEL

```bash
sudo yum install sqlite-devel
```

### Windows

Скачайте SQLite с официального сайта:
1. https://www.sqlite.org/download.html
2. Скачайте "Precompiled Binaries for Windows"
3. Распакуйте и добавьте в PATH

## Компиляция

### Linux / macOS

1. Перейдите в директорию VanitySearch:

```bash
cd VanitySearch
```

2. Обновите Makefile (должна быть строка с `-lsqlite3`):

```makefile
LFLAGS = -lpthread -lsqlite3
```

3. Компилируйте:

```bash
# CPU версия
make

# GPU версия (CUDA)
make gpu=1

# Очистка
make clean
```

### Проверка компиляции

```bash
./VanitySearch -v
```

Должна отобразиться версия VanitySearch.

### Тест базы данных

```bash
# Создайте тестовую базу
./VanitySearch -db bitcoin_addresses_optimized.sqlite -t 1

# Вы должны увидеть:
# [Database] Инициализация проверки базы данных...
# [Database] ✅ База данных готова к проверке
```

## Устранение проблем

### Ошибка: "sqlite3.h: No such file or directory"

SQLite не установлен или заголовочные файлы не найдены.

**Решение:**

```bash
# Проверьте установку
pkg-config --cflags --libs sqlite3

# Если не найден, установите
sudo apt-get install libsqlite3-dev
```

### Ошибка: "undefined reference to sqlite3_open_v2"

Библиотека SQLite не подключена при линковке.

**Решение:**

Добавьте `-lsqlite3` в LFLAGS в Makefile:

```makefile
LFLAGS = -lpthread -lsqlite3
```

### macOS: "library not found for -lsqlite3"

Используйте системный SQLite:

```bash
# Проверьте наличие
ls -l /usr/lib/libsqlite3*

# Компилируйте с явным путем
make LFLAGS="-lpthread -L/usr/lib -lsqlite3"
```

### Windows MSVC

1. Скачайте SQLite amalgamation (sqlite3.c, sqlite3.h)
2. Добавьте в проект:
   - `sqlite3.c` в исходные файлы
   - `sqlite3.h` в include path
3. Компилируйте как обычно

## Проверка установки

После успешной компиляции:

```bash
# Проверьте версию
./VanitySearch -v

# Проверьте справку (должна быть опция -db)
./VanitySearch -h | grep "\-db"
```

Должен быть вывод:

```
 -db database: Check generated addresses against SQLite database
```

## Готово!

Теперь VanitySearch готов к использованию с базой данных. См. [DATABASE_SEARCH_GUIDE.md](DATABASE_SEARCH_GUIDE.md) для инструкций по использованию.

