# Команды для запуска поиска на 4 CPU процессорах

## Диапазон поиска
- **Начало:** 2128350382728406075874
- **Конец:** 2128351282728406075898
- **Префикс:** `1PWo3JeB9jr`

## Разбиение
- Общий диапазон разбит на **4 части**
- Каждая часть разбита на **8 сегментов**
- Итого: **32 сегмента** (4 части × 8 сегментов)

---

## 4 команды для запуска (в отдельных терминалах)

### Процессор 1:
```bash
./VanitySearch -seg seg_part1.txt -bits 71 -t 1 -m 1000000 -o out_part1.txt "1PWo3JeB9jr" > log_part1.log 2>&1
```

### Процессор 2:
```bash
./VanitySearch -seg seg_part2.txt -bits 71 -t 1 -m 1000000 -o out_part2.txt "1PWo3JeB9jr" > log_part2.log 2>&1
```

### Процессор 3:
```bash
./VanitySearch -seg seg_part3.txt -bits 71 -t 1 -m 1000000 -o out_part3.txt "1PWo3JeB9jr" > log_part3.log 2>&1
```

### Процессор 4:
```bash
./VanitySearch -seg seg_part4.txt -bits 71 -t 1 -m 1000000 -o out_part4.txt "1PWo3JeB9jr" > log_part4.log 2>&1
```

---

## Автоматический запуск всех 4 процессов

Используйте скрипт `run_4cpu.sh`:

```bash
./run_4cpu.sh
```

Этот скрипт запустит все 4 процесса в фоне через `nohup`.

---

## Подсчет найденных кошельков

### Единая команда для просмотра количества найденных кошельков:

```bash
./count_found.sh
```

Или вручную:

```bash
echo "=== Найдено кошельков ===" && \
for f in out_part1.txt out_part2.txt out_part3.txt out_part4.txt; do \
  if [ -f "$f" ]; then \
    count=$(wc -l < "$f" 2>/dev/null || echo 0); \
    echo "$f: $count"; \
  fi; \
done && \
total=$(grep -h '^' out_part*.txt 2>/dev/null | wc -l); \
echo "Всего: $total"
```

---

## Мониторинг процессов

### Проверка статуса процессов:
```bash
ps aux | grep VanitySearch | grep -v grep
```

### Просмотр логов в реальном времени:
```bash
tail -f log_part*.log
```

### Просмотр конкретного лога:
```bash
tail -f log_part1.log
```

---

## Файлы результатов

- `out_part1.txt` - результаты процесса 1
- `out_part2.txt` - результаты процесса 2
- `out_part3.txt` - результаты процесса 3
- `out_part4.txt` - результаты процесса 4

---

## Файлы логов

- `log_part1.log` - лог процесса 1
- `log_part2.log` - лог процесса 2
- `log_part3.log` - лог процесса 3
- `log_part4.log` - лог процесса 4

---

## Остановка процессов

Если нужно остановить все процессы:

```bash
pkill -f "VanitySearch.*seg_part"
```

Или остановить конкретный процесс по PID (из вывода `ps aux`):

```bash
kill <PID>
```

