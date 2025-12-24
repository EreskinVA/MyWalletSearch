# Runbook (CPU/GPU) для VanitySearch

Этот файл — практическая инструкция “как правильно”:
- чистить процессы на сервере/локально
- собирать CPU и GPU версии
- запускать поиск в разных режимах (префикс, wildcard, префикс+суффикс, позиционная маска, сегменты)
- пользоваться прогрессом/автосейвом
- понимать ключевые параметры (`-g`, `-m`, `-t`, `-seg`, `-bits`, `-check` и т.д.)

Все примеры ниже предполагают, что вы находитесь в каталоге проекта:
- **сервер**: `~/MyWalletSearch` (пример)
- **локально**: `.../Projects/iiModel/VanitySearch`

---

## 1) Быстрая диагностика “всё ли живо”

### CPU процессы

```bash
pgrep -af VanitySearch || echo "OK: VanitySearch не запущен"
ps aux | egrep '[V]anitySearch|timeout .*VanitySearch' || echo "OK: процессов нет"
```

Остановка:

```bash
pkill -f VanitySearch || true
pkill -f 'timeout .*VanitySearch' || true
```

### GPU процессы (Linux, NVIDIA)

```bash
nvidia-smi
```

Если видите зависший процесс, убивайте по PID:

```bash
kill -TERM <PID>
sleep 2
kill -KILL <PID>
```

---

## 2) Сборка CPU (локально или на сервере без GPU)

### Очистка + сборка

```bash
cd VanitySearch
make clean
make -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu)"
```

### Самопроверка математики и адресов

```bash
./VanitySearch -check | tail -80
```

Ожидаемо:
- `Check Generator/Double/Add/GenKey :OK`
- все `Adress : ... OK!`
- если собрали без GPU — в конце нормально увидеть `GPU code not compiled...`

---

## 3) Сборка GPU (Linux + NVIDIA CUDA)

### 3.1 Очистка + сборка

```bash
cd VanitySearch
make clean
make gpu=1 CCAP=8.9 all -j"$(nproc)"
```

`CCAP=8.9` — для RTX 4090 (sm_89). Для другой карты меняйте compute capability.

### 3.2 Подбор grid `-g`

Рекомендуем сначала прогнать `-check` на небольшом `-g` (иначе возможен OOM):

```bash
./VanitySearch -m 4096 -g 64,128 -check
```

Важно:
- **параметр `-g` должен быть ДО `-check`**, иначе `-check` выполнится сразу и `-g` не применится.

Пример неправильного порядка:

```bash
./VanitySearch -check -g 64,128   # плохо
```

Пример правильного порядка:

```bash
./VanitySearch -g 64,128 -check   # хорошо
```

### 3.3 Если видите OOM / Kernel out of memory

Уменьшайте grid:
- `-g 64,128` → `-g 32,128` → `-g 16,128`

---

## 4) Базовые режимы запуска поиска

### 4.1 Простой префикс (fast path)

Пример: искать адреса, начинающиеся на `18ss`:

```bash
./VanitySearch -gpu -gpuId 0 -g 64,128 -t 2 -o out.txt 18ss
```

### 4.2 Wildcard (mask) / префикс+суффикс

Wildcard работает по правилу:
- `*` — любая последовательность символов
- `?` — любой один символ

Примеры:

```bash
# префикс+суффикс
./VanitySearch -gpu -gpuId 0 -g 64,128 -t 2 -o out_pref_suf.txt "1P*nt7pX"

# простой “лояльный” тест, который быстро даёт Found
./VanitySearch -gpu -gpuId 0 -g 64,128 -t 2 -m 2000000 -o out_fast.txt "1P*X"
```

Если видите:
`Warning, N items lost ...`  
значит переполняется буфер результатов.

Решения:
- увеличить `-m` (например `-m 2000000`)
- или уменьшить `-g`

### 4.3 Остановиться после первого найденного

```bash
./VanitySearch ... -stop -o out.txt "1P*X"
```

---

## 5) Сегментный поиск (`-seg`) — формат конфигурации

### 5.1 Формат файла сегментов

Одна строка = один сегмент:

```
startPercent endPercent direction [name]
```

Где:
- `startPercent`, `endPercent` — числа `0..100`
- `direction` — `up` или `down` (можно `вверх/вниз`)
- `name` — опциональное имя сегмента

Пример `seg_dir_test.txt` (разнонаправленный тест):

```txt
44.9900 44.9902 up   seg_up
44.9902 44.9900 down seg_down
```

**Важно про DOWN:**
- ожидается формат `startPercent > endPercent`
- DOWN идёт “сверху вниз” (от start к end)

### 5.2 Запуск сегментного поиска

Обязательны `-seg` и `-bits`:

```bash
./VanitySearch -seg seg_dir_test.txt -bits 71 -gpu -gpuId 0 -g 64,128 -t 2 -o out.txt 18ss
```

---

## 6) Прогресс / автосохранение / продолжение

### 6.1 Включить прогресс и автосейв

```bash
./VanitySearch \
  -seg seg_dir_test.txt -bits 71 \
  -gpu -gpuId 0 -g 64,128 -t 2 \
  -progress /root/MyWalletSearch/progress.dat -autosave 60 \
  -o out.txt \
  18ss
```

### 6.2 Продолжить из прогресса

```bash
./VanitySearch \
  -seg seg_dir_test.txt -bits 71 \
  -resume -progress /root/MyWalletSearch/progress.dat \
  -gpu -gpuId 0 -g 64,128 -t 2 \
  -o out.txt \
  18ss
```

### 6.3 Как проверить, что сегменты реально двигаются (up/down)

Прочитать ключевые поля из progress-файла:

```bash
egrep "Name=|Direction=|CurrentKey=|KeysChecked=" -n /root/MyWalletSearch/progress.dat
```

Ожидаемо:
- `Direction=0` (UP): `CurrentKey` монотонно растёт
- `Direction=1` (DOWN): `CurrentKey` монотонно уменьшается

---

## 7) Полезные параметры (кратко)

- **`-t N`**: число CPU потоков
- **`-gpu`**: включить GPU
- **`-gpuId 0[,1,...]`**: выбрать GPU
- **`-g X,Y`**: grid для GPU (например `64,128`)
- **`-m N`**: maxFound (буфер найденных кандидатов на GPU). Увеличивать при `items lost`.
- **`-o file`**: файл результатов
- **`-stop`**: остановить после первого найденного
- **`-seg file`**: файл сегментов
- **`-bits N`**: битовый диапазон (например `71`)
- **`-progress file`**: файл прогресса
- **`-autosave S`**: автосохранение каждые S секунд
- **`-resume`**: продолжить из прогресса
- **`-check`**: самопроверка (CPU + при наличии GPU — GPU/CPU check)

---

## 8) Частые ошибки и как их избежать

### 8.1 Неправильный порядок `-check`

`-check` исполняется сразу при парсинге аргументов, поэтому:

```bash
./VanitySearch -check -g 64,128   # -g не применится
```

Правильно:

```bash
./VanitySearch -g 64,128 -check
```

### 8.2 `items lost`

Увеличьте `-m` или уменьшите `-g`:

```bash
./VanitySearch ... -m 2000000 ...
```

### 8.3 `...` в команде

`...` — это не “placeholder” для VanitySearch, а реальный аргумент, который ломает парсинг:

```bash
./VanitySearch ... -stop ...   # будет "Unexpected ... argument"
```

---

## 9) (Опционально) Включение debug-логов

По умолчанию `DEBUG`-логи отключены. Включить можно сборкой с макросом:

```bash
make clean
make debug=1 CXXFLAGS="$CXXFLAGS -DVANITYSEARCH_DEBUG_LOGS" -j"$(nproc)"
```

---

## 10) Рекомендуемые “шаблонные” команды

### GPU: стабильный запуск на 4090

```bash
./VanitySearch -gpu -gpuId 0 -g 64,128 -t 2 -m 2000000 -o out.txt 18ss
```

### GPU: сегменты + прогресс

```bash
./VanitySearch \
  -seg segments.txt -bits 71 \
  -gpu -gpuId 0 -g 64,128 -t 2 -m 2000000 \
  -progress progress.dat -autosave 60 \
  -o results.txt \
  18ss
```


