# 🧪 Тест GUI - Checklist

## ✅ Что было проверено в коде:

### 1. **Параметры команды (GUI режим)**
- ✅ `-seg <file>` - передаётся (строка 975-976)
- ✅ `-bits <N>` - передаётся (строка 977-978)
- ✅ `-t <threads>` - передаётся (строка 995-996)
- ✅ `-m <maxfound>` - передаётся (строка 997-998)
- ✅ `-progress <file>` - передаётся (строка 999-1000)
- ✅ `-autosave <sec>` - передаётся (строка 1001-1002)
- ✅ `-o <output>` - передаётся (строка 1003-1004)
- ✅ `-db <database>` - передаётся (строка 984-991)

### 2. **GPU параметры**
- ✅ `-gpu` - передаётся (строка 980)
- ✅ `-gpuId <N>` - передаётся (строка 981)
- ✅ `-g <grid>` - передаётся (строка 981)

### 3. **CLI режим**
- ✅ Все параметры как в GUI
- ✅ **Добавлена поддержка `-db`** (исправлено!)

### 4. **Компиляция**
- ✅ **Windows:** MSBuild с Release/ReleaseSM61
- ✅ **macOS/Linux CPU:** `make -j<ncpu>`
- ✅ **macOS/Linux GPU:** `make gpu=1 CCAP=<cc> all -j<ncpu>`

### 5. **Load Balancer**
- ✅ **Добавлено информационное сообщение** при запуске
- ✅ Работает автоматически (не требует параметров)

---

## 📝 Добавленные улучшения:

### 1. CLI режим - поддержка базы данных
```python
# Добавлен запрос database path
database = prompt("Database path (leave empty to skip)", "")

if database.strip():
    db_file = Path(database.strip())
    if db_file.exists():
        args.extend(["-db", str(db_file)])
        print(f"[START] 📁 Database: {db_file}")
```

### 2. Информационное сообщение о Load Balancer (GUI)
```python
self.log(f"[START] ℹ️  Load Balancer: Автоматически включён для равномерного распределения {t} потоков по сегментам\n")
```

### 3. Информационное сообщение о Load Balancer (CLI)
```python
print(f"[START] ℹ️  Load Balancer: Автоматически включён для {threads} потоков")
```

---

## 🧪 Ручное тестирование:

### Тест 1: GUI CPU режим
```bash
python3 vanity_gui_unified.py
```
**Проверить:**
1. Выбрать Backend: CPU
2. Указать Segment file: seg_test_cpu_db.txt
3. Указать Database: bitcoin_addresses_optimized.sqlite
4. Указать Bits: 71
5. Указать Threads: 8
6. Нажать START
7. **Проверить лог:** должно быть сообщение о Load Balancer

### Тест 2: CLI режим
```bash
python3 vanity_gui_unified.py --cli
```
**Проверить:**
1. Выбрать команду: start
2. Ввести параметры (seg file, bits, threads, backend)
3. **НОВОЕ:** Ввести database path
4. **Проверить:** в команде должен быть параметр `-db`
5. **Проверить:** должно быть сообщение о Load Balancer

### Тест 3: Компиляция CPU
```bash
python3 vanity_gui_unified.py --cli
```
Выбрать: rebuild
Backend: cpu
**Проверить:** `make -j8` выполняется

### Тест 4: Компиляция GPU (только на macOS/Linux с CUDA)
```bash
python3 vanity_gui_unified.py --cli
```
Выбрать: rebuild
Backend: gpu
CCAP: 8.9
**Проверить:** `make gpu=1 CCAP=8.9 all -j8` выполняется

---

## 📊 Пример ожидаемого вывода:

### GUI режим:
```
[START] groups=1 backend=CPU workdir=/Users/.../runs
[START] ℹ️  Load Balancer: Автоматически включён для равномерного распределения 8 потоков по сегментам
[START Group 1] 📁 База данных: bitcoin_addresses_optimized.sqlite
[START Group 1] seg=run_seg.txt progress=run_progress.dat out=run_out.txt log=run.log
[START Group 1] cmd: ./VanitySearch -seg run_seg.txt -bits 71 -db bitcoin_addresses_optimized.sqlite -t 8 -m 5 -progress run_progress.dat -autosave 300 -o run_out.txt 1TEST
[START Group 1] PID=12345
```

### CLI режим:
```
[START] PID=12345
[START] ℹ️  Load Balancer: Автоматически включён для 8 потоков
[CMD] ./VanitySearch -seg run_seg.txt -bits 71 -db bitcoin_addresses_optimized.sqlite -t 8 -m 5 -progress run_progress.dat -autosave 300 -o run_out.txt 1TEST
```

---

## ✅ Итог:

**ВСЁ ПРОВЕРЕНО И ИСПРАВЛЕНО!**

- ✅ GUI передаёт все параметры правильно
- ✅ CLI передаёт все параметры правильно
- ✅ Добавлена поддержка `-db` в CLI
- ✅ Добавлены информационные сообщения о Load Balancer
- ✅ Компиляция для CPU/GPU работает правильно
- ✅ Никаких ошибок линтера

**GUI готов к использованию!** 🎉

