#!/usr/bin/env python3
"""
Скрипт для тестирования проверки базы данных VanitySearch.

Создает тестовый адрес с известным приватным ключом,
добавляет его в базу, запускает поиск в узком сегменте,
проверяет результат и удаляет тестовый адрес.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

# Конфигурация
DB_PATH = Path(__file__).parent / "bitcoin_addresses_optimized.sqlite"
VANITYSEARCH = Path(__file__).parent / "VanitySearch"

# Тестовый приватный ключ (в hex, 64 символа)
# Используем значение СРАЗУ после начала 71-битного диапазона для быстрого теста
# 71-битный диапазон начинается с: 0x400000000000000000
# Берём ключ: 0x400000000000000000 + 50 = 0x400000000000000032
TEST_PRIVATE_KEY_HEX = "0000000000000000000000000000000000000000000000000400000000000032"  # 32 байта
TEST_PRIVATE_KEY_DEC = str(int("400000000000000032", 16))  # 1180591620717411303474

# Ожидаемый адрес для этого ключа (compressed)
# Нужно вычислить используя VanitySearch
EXPECTED_ADDRESS = None  # Вычислим динамически


def run_command(cmd, capture=True):
    """Запуск команды и возврат результата."""
    print(f"[CMD] {' '.join(cmd)}")
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd)
        return result.returncode, "", ""


def get_address_for_key(private_key_hex):
    """
    Вычисляет Bitcoin адрес для приватного ключа.
    Использует VanitySearch с ключом -k для вычисления адреса.
    """
    # VanitySearch может вывести адрес если запустить с этим ключом
    # Но проще использовать Python библиотеку
    
    # Попробуем использовать ecdsa + hashlib + base58
    try:
        import ecdsa
        import hashlib
        import base58
    except ImportError:
        print("[ERROR] Требуются модули: ecdsa, base58")
        print("Установите: pip3 install ecdsa base58")
        return None
    
    # Преобразуем hex ключ в байты
    private_key_bytes = bytes.fromhex(private_key_hex)
    
    # Создаем приватный ключ SECP256k1
    sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    
    # Получаем публичный ключ (compressed format)
    public_key_bytes = vk.to_string()
    x = int.from_bytes(public_key_bytes[:32], 'big')
    y = int.from_bytes(public_key_bytes[32:], 'big')
    
    # Compressed public key
    if y % 2 == 0:
        compressed_public_key = b'\x02' + x.to_bytes(32, 'big')
    else:
        compressed_public_key = b'\x03' + x.to_bytes(32, 'big')
    
    # SHA256 -> RIPEMD160
    sha256_hash = hashlib.sha256(compressed_public_key).digest()
    ripemd160 = hashlib.new('ripemd160', sha256_hash).digest()
    
    # Добавляем версию (0x00 для mainnet)
    versioned = b'\x00' + ripemd160
    
    # Checksum
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    
    # Base58 encode
    address = base58.b58encode(versioned + checksum).decode('ascii')
    
    return address


def add_address_to_db(db_path, address):
    """Добавляет тестовый адрес в базу данных."""
    print(f"\n[DB] Добавляем тестовый адрес в базу: {address}")
    
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None  # Autocommit mode
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже
    cursor.execute("SELECT COUNT(*) FROM addresses WHERE address = ?", (address,))
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"[DB] Адрес уже есть в базе")
    else:
        cursor.execute("INSERT INTO addresses (address) VALUES (?)", (address,))
        # Explicit commit and sync
        cursor.execute("PRAGMA synchronous = FULL")
        print(f"[DB] ✅ Адрес добавлен и зафиксирован в базе")
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM addresses WHERE address = ?", (address,))
        verify_count = cursor.fetchone()[0]
        if verify_count == 1:
            print(f"[DB] ✅ Проверка: адрес найден в базе")
        else:
            print(f"[DB] ❌ ОШИБКА: адрес НЕ найден после вставки!")
    
    conn.close()
    
    # Second verification with new connection
    conn2 = sqlite3.connect(db_path)
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT COUNT(*) FROM addresses WHERE address = ?", (address,))
    final_count = cursor2.fetchone()[0]
    conn2.close()
    
    if final_count == 1:
        print(f"[DB] ✅ Финальная проверка (новое подключение): адрес в базе")
    else:
        print(f"[DB] ❌ КРИТИЧЕСКАЯ ОШИБКА: адрес НЕ виден в новом подключении!")


def remove_address_from_db(db_path, address):
    """Удаляет тестовый адрес из базы данных."""
    print(f"\n[DB] Удаляем тестовый адрес из базы: {address}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM addresses WHERE address = ?", (address,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        print(f"[DB] ✅ Адрес удален из базы ({deleted} строк)")
    else:
        print(f"[DB] ⚠️  Адрес не найден в базе")


def create_test_segment(private_key_dec, segment_file, range_size=10):
    """Создает файл сегмента вокруг тестового ключа."""
    key_int = int(private_key_dec)
    start = max(1, key_int - range_size)
    end = key_int + range_size
    
    content = f"# Тестовый сегмент для проверки database check\n"
    content += f"# Приватный ключ находится внутри диапазона: {key_int} (hex: {hex(key_int)})\n"
    content += f"# Диапазон: {start} -> {end}\n"
    content += f"abs {start} {end} up test_segment 5\n"
    
    segment_file.write_text(content, encoding='utf-8')
    print(f"\n[SEGMENT] Создан файл сегмента: {segment_file}")
    print(f"[SEGMENT] Целевой ключ: {key_int} (hex: {hex(key_int)})")
    print(f"[SEGMENT] Диапазон поиска: {start} -> {end}")
    print(f"[SEGMENT] Размер: {end - start + 1} ключей (~{(end - start + 1) * 6} проверок с эндоморфизмами)")
    print(f"[SEGMENT] Ожидаемое время: ~{(end - start + 1) / 30000:.1f} сек при 0.03 Mkey/s")


def run_test_search(segment_file, db_path, output_file, timeout_sec=30):
    """Запускает VanitySearch с тестовым сегментом."""
    print(f"\n[SEARCH] Запуск VanitySearch (timeout {timeout_sec}s)...")
    
    cmd = [
        str(VANITYSEARCH),
        "-seg", str(segment_file),
        "-bits", "71",  # Обязательный параметр для -seg
        "-t", "2",
        "-db", str(db_path),
        "-o", str(output_file),
        "1*"  # Широкий паттерн чтобы не фильтровать
    ]
    
    print(f"[CMD] {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        rc = result.returncode
        stdout = result.stdout
    except subprocess.TimeoutExpired:
        print(f"[SEARCH] ⚠️  Timeout {timeout_sec}s истек, останавливаем поиск...")
        rc = -1
        stdout = "(timeout)"
    
    print(f"\n[SEARCH] Завершено с кодом: {rc}")
    if stdout and stdout != "(timeout)":
        # Выводим только последние строки
        lines = stdout.strip().split('\n')
        print("Последние 10 строк вывода:")
        for line in lines[-10:]:
            print(f"  {line}")
    
    return True  # Всегда возвращаем True, проверим результаты отдельно


def check_results(output_file, expected_address):
    """Проверяет результаты поиска."""
    db_found_file = output_file.parent / (output_file.stem + "_DatabaseFound.txt")
    
    print(f"\n[CHECK] Проверка результатов...")
    print(f"[CHECK] Файл с совпадениями: {db_found_file}")
    
    if not db_found_file.exists():
        print(f"[CHECK] ❌ ОШИБКА: Файл с результатами не найден!")
        print(f"[CHECK] Ожидался адрес: {expected_address}")
        return False
    
    # Читаем содержимое
    content = db_found_file.read_text(encoding='utf-8')
    lines = content.strip().split('\n')
    
    print(f"[CHECK] Найдено совпадений: {len(lines)}")
    
    # Ищем наш адрес
    found = False
    for line in lines:
        if expected_address in line:
            print(f"[CHECK] ✅ УСПЕХ! Тестовый адрес найден!")
            print(f"[CHECK] Строка: {line}")
            found = True
            break
    
    if not found:
        print(f"[CHECK] ❌ ОШИБКА: Тестовый адрес НЕ найден в результатах!")
        print(f"[CHECK] Ожидался: {expected_address}")
        print(f"[CHECK] Содержимое файла:")
        for line in lines[:5]:
            print(f"  {line}")
    
    return found


def main():
    print("=" * 70)
    print("ТЕСТ ПРОВЕРКИ БАЗЫ ДАННЫХ VANITYSEARCH")
    print("=" * 70)
    
    # Проверяем наличие файлов
    if not DB_PATH.exists():
        print(f"[ERROR] База данных не найдена: {DB_PATH}")
        return 1
    
    if not VANITYSEARCH.exists():
        print(f"[ERROR] VanitySearch не найден: {VANITYSEARCH}")
        return 1
    
    # Вычисляем адрес для тестового ключа
    print(f"\n[STEP 1] Вычисление адреса для тестового ключа...")
    print(f"[KEY] Приватный ключ (hex): {TEST_PRIVATE_KEY_HEX}")
    print(f"[KEY] Приватный ключ (dec): {TEST_PRIVATE_KEY_DEC}")
    
    test_address = get_address_for_key(TEST_PRIVATE_KEY_HEX)
    if not test_address:
        print(f"[ERROR] Не удалось вычислить адрес")
        return 1
    
    print(f"[KEY] ✅ Адрес: {test_address}")
    
    # Создаем временные файлы
    test_dir = Path(__file__).parent / "test_db_check"
    test_dir.mkdir(exist_ok=True)
    
    segment_file = test_dir / "test_segment.txt"
    output_file = test_dir / "test_output.txt"
    
    test_address_added = False
    
    try:
        # Шаг 2: Добавляем адрес в базу
        print(f"\n[STEP 2] Добавление адреса в базу данных...")
        add_address_to_db(DB_PATH, test_address)
        test_address_added = True
        
        # Шаг 3: Создаем сегмент (очень узкий для быстрого теста!)
        print(f"\n[STEP 3] Создание тестового сегмента...")
        create_test_segment(TEST_PRIVATE_KEY_DEC, segment_file, range_size=10)
        
        # Шаг 4: Запускаем поиск с timeout (увеличен для загрузки базы)
        print(f"\n[STEP 4] Запуск VanitySearch...")
        run_test_search(segment_file, DB_PATH, output_file, timeout_sec=60)
        
        # Шаг 5: Проверяем результаты
        print(f"\n[STEP 5] Проверка результатов...")
        found = check_results(output_file, test_address)
        
        # Итоговый результат
        print("\n" + "=" * 70)
        if found:
            print("✅ ТЕСТ ПРОЙДЕН! Проверка базы данных работает корректно!")
        else:
            print("❌ ТЕСТ ПРОВАЛЕН! Проверка базы данных не работает или работает неправильно!")
        print("=" * 70)
        
        return 0 if found else 1
        
    finally:
        # Шаг 6: Очистка - ВСЕГДА удаляем тестовый адрес из базы!
        if test_address_added:
            print(f"\n[STEP 6] Очистка: удаление тестового адреса из базы...")
            remove_address_from_db(DB_PATH, test_address)
            print(f"[CLEANUP] ✅ Тестовый адрес удален из базы")
        print(f"[CLEANUP] Тестовые файлы находятся в: {test_dir}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Тест прерван пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

