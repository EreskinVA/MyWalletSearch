#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конвертер базы данных LMDB → SQLite (только адреса)

Назначение:
- Преобразует базу данных LMDB (адреса + балансы) в компактную SQLite базу (только адреса)
- Создает индексированную базу для быстрого поиска
- Уменьшает размер базы с ~10 GB до ~1.5-2 GB

Использование:
    python3 convert_lmdb_to_sqlite.py [--input INPUT_DB] [--output OUTPUT_DB]
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import lmdb
except ImportError:
    print("❌ Ошибка: модуль lmdb не установлен")
    print("   Установите: pip3 install lmdb")
    sys.exit(1)


class LMDBToSQLiteConverter:
    """Конвертер LMDB → SQLite"""
    
    def __init__(self, lmdb_path: str, sqlite_path: str):
        self.lmdb_path = lmdb_path
        self.sqlite_path = sqlite_path
        self.batch_size = 100000  # Записей в одной транзакции
        
    def convert(self, *, auto_confirm: bool = False) -> bool:
        """Выполняет конвертацию"""
        
        print("=" * 70)
        print("🔄 Конвертация LMDB → SQLite (только адреса)")
        print("=" * 70)
        print()
        
        # Проверка входного файла
        if not os.path.exists(self.lmdb_path):
            print(f"❌ Ошибка: LMDB база не найдена: {self.lmdb_path}")
            return False
        
        # Проверка размера LMDB
        try:
            data_mdb = os.path.join(self.lmdb_path, 'data.mdb')
            if os.path.exists(data_mdb):
                lmdb_size = os.path.getsize(data_mdb)
                print(f"📊 Исходная LMDB база:")
                print(f"   Путь: {self.lmdb_path}")
                print(f"   Размер: {lmdb_size / (1024**3):.2f} GB")
            else:
                print(f"📊 Исходная LMDB база: {self.lmdb_path}")
        except Exception as e:
            print(f"⚠️  Не удалось определить размер LMDB: {e}")
        
        # Открываем LMDB и считаем записи
        print()
        print("📂 Открываем LMDB базу...")
        try:
            env = lmdb.open(self.lmdb_path, readonly=True, max_readers=1)
        except Exception as e:
            print(f"❌ Ошибка открытия LMDB: {e}")
            return False
        
        with env.begin() as txn:
            stat = env.stat()
            total_entries = stat['entries']
            print(f"✅ Найдено записей: {total_entries:,}")
            
            # Оценка размера SQLite
            avg_address_size = 34  # байт
            overhead = 20  # байт на запись (SQLite overhead)
            estimated_size = total_entries * (avg_address_size + overhead)
            estimated_size_gb = estimated_size / (1024**3)
            
            print()
            print(f"📈 Оценка результата:")
            print(f"   SQLite база (данные): ~{estimated_size / (1024**2):.0f} MB")
            print(f"   SQLite база (с индексом): ~{estimated_size_gb:.2f} GB")
            print(f"   Экономия: ~{(lmdb_size - estimated_size) / (1024**3):.2f} GB" 
                  if 'lmdb_size' in locals() else "")
        
        # Подтверждение
        if not auto_confirm:
            print()
            response = input("❓ Начать конвертацию? (y/n): ").strip().lower()
            if response not in ['y', 'yes', 'д', 'да']:
                print("❌ Конвертация отменена")
                env.close()
                return False
        
        # Удаляем старую SQLite базу если существует
        if os.path.exists(self.sqlite_path):
            print()
            print(f"🗑️  Удаляем старую SQLite базу: {self.sqlite_path}")
            try:
                os.remove(self.sqlite_path)
            except Exception as e:
                print(f"❌ Ошибка удаления: {e}")
                env.close()
                return False
        
        # Создаем SQLite базу
        print()
        print("📂 Создаем SQLite базу...")
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Создаем таблицу
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS addresses (
                    address TEXT PRIMARY KEY NOT NULL
                )
            """)
            
            # Оптимизация для быстрой вставки
            cursor.execute("PRAGMA synchronous = OFF")
            cursor.execute("PRAGMA journal_mode = MEMORY")
            cursor.execute("PRAGMA cache_size = 100000")
            
            conn.commit()
            print("✅ Таблица создана")
            
        except Exception as e:
            print(f"❌ Ошибка создания SQLite базы: {e}")
            env.close()
            return False
        
        # Конвертация данных
        print()
        print("🔄 Конвертация данных...")
        print()
        
        start_time = time.time()
        total_imported = 0
        last_report_time = start_time
        
        try:
            with env.begin() as txn:
                cursor_lmdb = txn.cursor()
                
                # Начинаем транзакцию
                conn.execute("BEGIN TRANSACTION")
                
                for key, value in cursor_lmdb:
                    try:
                        # Извлекаем только адрес (ключ)
                        address = key.decode('utf-8', errors='ignore')
                        
                        # Вставляем в SQLite (игнорируем дубликаты)
                        cursor.execute("INSERT OR IGNORE INTO addresses (address) VALUES (?)", 
                                     (address,))
                        
                        total_imported += 1
                        
                        # Периодический коммит и отчет
                        if total_imported % self.batch_size == 0:
                            conn.commit()
                            conn.execute("BEGIN TRANSACTION")
                            
                            # Отчет о прогрессе
                            current_time = time.time()
                            if current_time - last_report_time >= 2.0:
                                elapsed = current_time - start_time
                                rate = total_imported / elapsed if elapsed > 0 else 0
                                pct = (total_imported / total_entries * 100) if total_entries > 0 else 0
                                eta = (total_entries - total_imported) / rate if rate > 0 else 0
                                
                                print(f"   Обработано: {total_imported:,} / {total_entries:,} "
                                      f"({pct:.1f}%) | "
                                      f"Скорость: {rate:.0f} адр/сек | "
                                      f"ETA: {eta:.0f}с")
                                
                                last_report_time = current_time
                        
                    except Exception as e:
                        print(f"⚠️  Ошибка при обработке записи: {e}")
                        continue
                
                # Финальный коммит
                conn.commit()
                
        except Exception as e:
            print(f"❌ Ошибка при конвертации: {e}")
            conn.rollback()
            conn.close()
            env.close()
            return False
        
        env.close()
        
        # Создаем индекс
        print()
        print("📑 Создаем индекс для быстрого поиска...")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_address ON addresses(address)")
            conn.commit()
            print("✅ Индекс создан")
        except Exception as e:
            print(f"⚠️  Ошибка создания индекса: {e}")
        
        # Оптимизация базы
        print()
        print("⚙️  Оптимизация базы данных...")
        try:
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
            conn.commit()
            print("✅ Оптимизация завершена")
        except Exception as e:
            print(f"⚠️  Ошибка оптимизации: {e}")
        
        conn.close()
        
        # Финальная статистика
        elapsed_time = time.time() - start_time
        
        print()
        print("=" * 70)
        print("✅ КОНВЕРТАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 70)
        print()
        print(f"📊 Результаты:")
        print(f"   Обработано записей: {total_imported:,}")
        print(f"   Время: {elapsed_time:.1f} секунд")
        print(f"   Скорость: {total_imported / elapsed_time:.0f} адр/сек")
        
        # Размер результата
        if os.path.exists(self.sqlite_path):
            sqlite_size = os.path.getsize(self.sqlite_path)
            print(f"   Размер SQLite базы: {sqlite_size / (1024**3):.2f} GB")
            
            if 'lmdb_size' in locals():
                saved = lmdb_size - sqlite_size
                saved_pct = (saved / lmdb_size * 100) if lmdb_size > 0 else 0
                print(f"   Экономия: {saved / (1024**3):.2f} GB ({saved_pct:.1f}%)")
        
        print()
        print(f"💾 Новая база данных: {self.sqlite_path}")
        print()
        
        return True
    
    def test_performance(self, num_tests: int = 1000) -> None:
        """Тестирует скорость поиска в SQLite базе"""
        
        if not os.path.exists(self.sqlite_path):
            print(f"❌ SQLite база не найдена: {self.sqlite_path}")
            return
        
        print()
        print("=" * 70)
        print("⚡ Тест производительности SQLite")
        print("=" * 70)
        print()
        
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Получаем случайные адреса для тестирования
            cursor.execute(f"SELECT address FROM addresses LIMIT {num_tests}")
            test_addresses = [row[0] for row in cursor.fetchall()]
            
            if not test_addresses:
                print("❌ В базе нет адресов для тестирования")
                conn.close()
                return
            
            print(f"📋 Тестирование на {len(test_addresses)} адресах...")
            print()
            
            # Тест поиска
            start = time.time()
            found = 0
            
            for addr in test_addresses:
                cursor.execute("SELECT 1 FROM addresses WHERE address = ? LIMIT 1", (addr,))
                if cursor.fetchone():
                    found += 1
            
            elapsed = time.time() - start
            avg_time_us = (elapsed / len(test_addresses)) * 1_000_000
            
            print(f"✅ Результаты теста:")
            print(f"   Проверено адресов: {len(test_addresses)}")
            print(f"   Найдено: {found}")
            print(f"   Общее время: {elapsed:.3f} секунд")
            print(f"   Среднее время на поиск: {avg_time_us:.2f} микросекунд")
            print(f"   Скорость: {len(test_addresses) / elapsed:.0f} проверок/сек")
            print()
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Конвертер LMDB → SQLite (только адреса)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Конвертация с параметрами по умолчанию
  python3 convert_lmdb_to_sqlite.py

  # Указание путей к базам
  python3 convert_lmdb_to_sqlite.py \\
    --input /path/to/bitcoin_addresses.db \\
    --output /path/to/bitcoin_addresses.sqlite

  # Автоматическое подтверждение (без запроса)
  python3 convert_lmdb_to_sqlite.py --yes

  # С тестом производительности
  python3 convert_lmdb_to_sqlite.py --test
        """
    )
    
    parser.add_argument(
        "--input",
        default="/Users/vladimirereskin/Projects/BitcoinSearch/bitcoin_addresses.db",
        help="Путь к LMDB базе (по умолчанию: BitcoinSearch/bitcoin_addresses.db)"
    )
    
    parser.add_argument(
        "--output",
        default="bitcoin_addresses_optimized.sqlite",
        help="Путь для SQLite базы (по умолчанию: bitcoin_addresses_optimized.sqlite)"
    )
    
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Автоматическое подтверждение (пропустить запрос)"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Запустить тест производительности после конвертации"
    )
    
    args = parser.parse_args()
    
    # Конвертация
    converter = LMDBToSQLiteConverter(args.input, args.output)
    success = converter.convert(auto_confirm=args.yes)
    
    if not success:
        return 1
    
    # Тест производительности
    if args.test:
        converter.test_performance(num_tests=1000)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

