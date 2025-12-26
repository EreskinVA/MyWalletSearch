# Пошаговая инструкция: проверка соседних ключей (±256)

## Шаг 1: Проверить наличие найденных ключей

Убедитесь что в out-файлах есть найденные ключи с полем `PuzzleKeyAbs (DEC)`:

```bash
cd /Users/vladimirereskin/Projects/iiModel/VanitySearch

# Проверка какие файлы есть
ls -lh out_cpu_p*.txt

# Проверка что в них есть PuzzleKeyAbs
for f in out_cpu_p*.txt; do
    echo "=== $f ==="
    grep -c "PuzzleKeyAbs (DEC)" "$f" 2>/dev/null || echo "Не найдено"
done
```

**Ожидаемый результат:** Числа > 0 (количество найденных ключей в каждом файле)

---

## Шаг 2: Генерация сегментов для соседних ключей

Создаём файл сегментов из найденных ключей:

```bash
# Укажите ваши out-файлы (если названия отличаются от out_cpu_p1.txt, out_cpu_p2.txt, out_cpu_p3.txt)
python3 generate_segments_neighbors.py out_cpu_p1.txt out_cpu_p2.txt out_cpu_p3.txt > seg_neighbors.txt

# Проверка созданного файла
head -20 seg_neighbors.txt
echo "..."
tail -5 seg_neighbors.txt

# Подсчёт сегментов
grep -c "^abs " seg_neighbors.txt
```

**Ожидаемый результат:** 
- Файл `seg_neighbors.txt` создан
- Видны строки типа `abs 2026682282231556068624 2026682282231556071408 up neighbor_1 1`
- Количество сегментов = количеству уникальных найденных ключей

---

## Шаг 3: Проверка/настройка паттерна

Отредактируйте паттерн в скрипте (если нужно):

```bash
# Посмотреть текущий паттерн
grep "PATTERN=" run_neighbors_check.sh

# Если нужно изменить, отредактируйте файл:
# nano run_neighbors_check.sh
# или
# vim run_neighbors_check.sh
```

**Текущий паттерн:** `1PWo3JeB9jr` (можно оставить или изменить)

---

## Шаг 4: Запуск проверки

```bash
# Просто запустите скрипт
./run_neighbors_check.sh
```

**Что происходит:**
1. Скрипт автоматически генерирует `seg_neighbors.txt` (если его нет)
2. Запускает `VanitySearch` с созданными сегментами
3. Результаты пишутся в `out_neighbors.txt`
4. Лог в `log_neighbors.log`

---

## Шаг 5: Проверка результатов

```bash
# Количество найденных
wc -l out_neighbors.txt

# Просмотр найденных адресов
cat out_neighbors.txt

# Лог (если нужно)
tail -30 log_neighbors.log
```

---

## Вариант 2: Ручной запуск (если нужно больше контроля)

Если хотите запустить вручную:

```bash
# 1. Создать сегменты
python3 generate_segments_neighbors.py out_cpu_p1.txt out_cpu_p2.txt out_cpu_p3.txt > seg_neighbors.txt

# 2. Проверить сегменты
cat seg_neighbors.txt

# 3. Запустить VanitySearch напрямую
./VanitySearch \
    -seg seg_neighbors.txt \
    -bits 71 \
    -t 9 \
    -m 10000 \
    -o out_neighbors.txt \
    "1PWo3JeB9jr" \
    > log_neighbors.log 2>&1

# 4. Проверить результаты
cat out_neighbors.txt
```

---

## Возможные проблемы

### Проблема: "не удалось создать сегменты или не найдено ключей"

**Решение:**
```bash
# Проверьте что в out-файлах есть PuzzleKeyAbs
grep "PuzzleKeyAbs (DEC)" out_cpu_p*.txt

# Если нет - значит ключи ещё не найдены или файлы имеют другой формат
```

### Проблема: VanitySearch не найден

**Решение:**
```bash
# Пересоберите проект
make clean && make -j"$(sysctl -n hw.ncpu)"
```

### Проблема: Файлы называются по-другому

**Решение:** Отредактируйте `run_neighbors_check.sh`:
```bash
# Найдите строку:
OUT_FILES="out_cpu_p1.txt out_cpu_p2.txt out_cpu_p3.txt"

# Замените на ваши файлы:
OUT_FILES="ваш_файл1.txt ваш_файл2.txt"
```


