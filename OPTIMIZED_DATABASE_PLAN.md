# 🚀 План создания оптимизированной базы данных только с адресами

## 📊 Текущая ситуация

- **Текущая база**: LMDB с адресами + балансами
- **Размер**: 10 GB
- **Записей**: 23,299,529 адресов
- **Проблема**: Хранятся балансы, которые не нужны для ванити-поиска

## 🎯 Цель

Создать базу данных только с адресами (без балансов):
- ✅ **Меньше места** (10 GB → 1-2 GB, экономия 80-90%)
- ✅ **Быстрее работает** (меньше данных для обработки)
- ✅ **Быстрее загружается** в память (если нужно)

---

## 📋 Сравнение вариантов

| Формат | Размер | Скорость поиска | Память | Сложность | Рекомендация |
|--------|--------|-----------------|--------|-----------|--------------|
| **SQLite с индексом** | ~1.5-2 GB | O(log n) ~50-100ns | ~50 MB | Низкая | ⭐⭐⭐⭐⭐ **ЛУЧШИЙ** |
| **LMDB (только ключи)** | ~1.2 GB | O(log n) ~50-100ns | ~100 MB | Средняя | ⭐⭐⭐⭐ Отлично |
| Бинарный файл (отсортированный) | ~1.0 GB | O(log n) ~200ns | Минимальная | Низкая | ⭐⭐⭐ Хорошо |
| Hash-файл (custom) | ~1.1 GB | O(1) ~10ns | ~100 MB | Высокая | ⭐⭐ Сложно |

---

## ✅ Рекомендуемое решение: SQLite с индексом

### Почему SQLite?

1. **Размер**: ~1.5-2 GB (в 5-7 раз меньше текущей базы)
2. **Скорость**: Очень быстрая (достаточно для ванити-поиска)
3. **Простота**: Легко интегрировать в C++ код
4. **Универсальность**: Работает везде, стандартная библиотека
5. **Индексирование**: Автоматическое, оптимизированное

### Структура базы

```sql
CREATE TABLE addresses (
    address TEXT PRIMARY KEY
);

CREATE INDEX idx_address ON addresses(address);
```

### Оценка размера

- Количество адресов: 23,299,529
- Средний размер адреса: 34 байта
- Overhead SQLite: ~20 байт на запись
- **Итого**: ~23M × 54 байта = ~1.2 GB (данные)
- Индекс: ~400-600 MB
- **Общий размер**: ~1.5-2 GB

---

## 🔄 Альтернатива: LMDB (только ключи)

### Почему LMDB тоже хорош?

1. **Размер**: ~1.2 GB (в 8 раз меньше)
2. **Скорость**: Максимальная (memory-mapped)
3. **Память**: Минимальное потребление (~100 MB)
4. **Уже используется**: В проекте уже есть опыт работы с LMDB

### Структура

- Только ключи (адреса)
- Без значений (балансы)
- Автоматическое B-дерево индексирование

### Оценка размера

- Количество адресов: 23,299,529
- Размер ключа: 34 байта
- Overhead LMDB: ~16 байт
- **Итого**: ~23M × 50 байт = ~1.15 GB

---

## 🛠️ План реализации

### Вариант 1: SQLite (РЕКОМЕНДУЕТСЯ)

#### Шаг 1: Создание скрипта конвертации

```python
# convert_to_optimized_db.py
import lmdb
import sqlite3
import os

def convert_lmdb_to_sqlite(lmdb_path, sqlite_path):
    """Конвертирует LMDB базу в SQLite (только адреса)"""
    
    # Создаем SQLite базу
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE addresses (address TEXT PRIMARY KEY)")
    cursor.execute("CREATE INDEX idx_address ON addresses(address)")
    
    # Открываем LMDB
    env = lmdb.open(lmdb_path, readonly=True, max_readers=1)
    
    # Конвертируем
    batch_size = 100000
    count = 0
    
    with env.begin() as txn:
        cursor_lmdb = txn.cursor()
        
        for key, value in cursor_lmdb:
            address = key.decode('utf-8')
            cursor.execute("INSERT OR IGNORE INTO addresses VALUES (?)", (address,))
            count += 1
            
            if count % batch_size == 0:
                conn.commit()
                print(f"Обработано: {count:,} адресов...")
    
    conn.commit()
    conn.close()
    env.close()
    
    print(f"✅ Готово! Обработано {count:,} адресов")
    print(f"Размер новой базы: {os.path.getsize(sqlite_path) / (1024**3):.2f} GB")

if __name__ == "__main__":
    convert_lmdb_to_sqlite("bitcoin_addresses.db", "bitcoin_addresses_only.db")
```

#### Шаг 2: Интеграция в VanitySearch (C++)

```cpp
#include <sqlite3.h>

class VanitySearch {
private:
    sqlite3* db;
    sqlite3_stmt* check_stmt;
    
    bool openDatabase(const std::string& dbPath) {
        int rc = sqlite3_open_v2(dbPath.c_str(), &db, 
                                  SQLITE_OPEN_READONLY, NULL);
        if (rc != SQLITE_OK) {
            return false;
        }
        
        // Подготовить запрос для проверки адреса
        const char* sql = "SELECT 1 FROM addresses WHERE address = ? LIMIT 1";
        rc = sqlite3_prepare_v2(db, sql, -1, &check_stmt, NULL);
        return (rc == SQLITE_OK);
    }
    
    bool isAddressInDatabase(const std::string& addr) {
        sqlite3_reset(check_stmt);
        sqlite3_bind_text(check_stmt, 1, addr.c_str(), -1, SQLITE_STATIC);
        int rc = sqlite3_step(check_stmt);
        return (rc == SQLITE_ROW);
    }
};
```

**Преимущества SQLite в C++:**
- Встроенная библиотека (`sqlite3.h`)
- Простая интеграция
- Автоматическое кэширование
- Подготовленные запросы (очень быстро)

---

### Вариант 2: LMDB (только ключи)

#### Шаг 1: Создание оптимизированной LMDB базы

```python
# create_optimized_lmdb.py
import lmdb
import os

def create_optimized_lmdb(source_lmdb, target_lmdb):
    """Создает новую LMDB базу только с адресами"""
    
    # Удаляем старую если есть
    if os.path.exists(target_lmdb):
        import shutil
        shutil.rmtree(target_lmdb)
    
    # Открываем исходную базу
    source_env = lmdb.open(source_lmdb, readonly=True, max_readers=1)
    
    # Создаем новую базу
    map_size = 2 * 1024 * 1024 * 1024  # 2 GB
    target_env = lmdb.open(target_lmdb, map_size=map_size, 
                           max_dbs=0, sync=False, writemap=True)
    
    count = 0
    with source_env.begin() as source_txn:
        with target_env.begin(write=True) as target_txn:
            cursor = source_txn.cursor()
            
            for key, value in cursor:
                # Копируем только ключ (адрес), без значения
                target_txn.put(key, b'')  # Пустое значение
                count += 1
                
                if count % 100000 == 0:
                    target_txn.commit()
                    target_txn = target_env.begin(write=True)
                    print(f"Обработано: {count:,} адресов...")
    
    source_env.close()
    target_env.close()
    
    print(f"✅ Готово! Обработано {count:,} адресов")
    size = sum(os.path.getsize(os.path.join(target_lmdb, f)) 
               for f in os.listdir(target_lmdb) 
               if os.path.isfile(os.path.join(target_lmdb, f)))
    print(f"Размер новой базы: {size / (1024**3):.2f} GB")

if __name__ == "__main__":
    create_optimized_lmdb("bitcoin_addresses.db", "bitcoin_addresses_only.db")
```

#### Шаг 2: Использование в VanitySearch

Код уже есть в проекте (BitcoinSearch), можно адаптировать.

---

## 📊 Сравнение результатов

### Текущая база (LMDB с балансами)
- Размер: **10 GB**
- Время загрузки в память: ~30-60 секунд
- Размер в памяти: ~1.8 GB (если загружать все)
- Скорость поиска: ~100 ns

### Оптимизированная база (SQLite или LMDB только адреса)
- Размер: **1.2-2 GB** (экономия 80-90%)
- Время загрузки в память: ~5-10 секунд (если нужно)
- Размер в памяти: ~1.1 GB (если загружать все)
- Скорость поиска: ~50-100 ns (примерно та же)

**Преимущества:**
- ✅ В 5-8 раз меньше место на диске
- ✅ В 3-6 раз быстрее загрузка
- ✅ Меньше потребление памяти
- ✅ Та же скорость поиска

---

## 🎯 Финальная рекомендация

### **Выбрать SQLite с индексом**

**Причины:**
1. ✅ Легче интегрировать в C++ (стандартная библиотека)
2. ✅ Универсальный формат (можно использовать везде)
3. ✅ Автоматическая оптимизация
4. ✅ Размер приемлемый (~1.5-2 GB)
5. ✅ Скорость достаточная для ванити-поиска

### План действий:

1. ✅ Создать скрипт конвертации LMDB → SQLite
2. ✅ Протестировать размер и скорость
3. ✅ Интегрировать SQLite в VanitySearch
4. ✅ Заменить использование текущей базы
5. ✅ Протестировать на реальных данных

**Время реализации:** ~2-4 часа
**Экономия места:** ~8 GB (80% от текущего размера)
**Улучшение скорости загрузки:** В 3-6 раз быстрее



