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

Единицы измерения:
K = тысяча (10³)
M = миллион (10⁶)
G = миллиард (10⁹)
T = триллион (10¹²)

---

## 0) Windows (локально): сборка и запуск (Visual Studio / MSBuild)

Ниже — “правильные” команды для Windows 10/11 + NVIDIA.

### 0.1 Быстрая проверка GPU и Compute Capability

В PowerShell:

```powershell
nvidia-smi
nvidia-smi -L
nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader
```

Ожидаемо вы увидите что-то вроде:
- `CUDA Version: 12.x` (это версия, поддерживаемая драйвером)
- `compute_cap: 6.1 / 7.5 / 8.6 / 8.9 ...`

### 0.2 Важное про CUDA версии и старые GPU (GTX 10xx / Pascal)

- **CUDA 13.x не поддерживает Pascal (sm_61)** → сборка GPU под GTX 1050 Ti/1060/1070/1080 на CUDA 13.x будет падать.
- Для GTX 10xx используйте **CUDA 11.8** (рекомендуется) и сборку под **`sm_61`**.

### 0.3 Сборка в Visual Studio (рекомендуется)

Откройте `VanitySearch.sln` и выберите конфигурацию:

- **`ReleaseSM61 | x64`** — для **GTX 1050 Ti (sm_61)** (использует CUDA 11.8).
- **`Release | x64`** — для современных GPU (например RTX 20/30/40) на более новых CUDA.

Затем `Build -> Build Solution`.

Выходной файл будет в:
- `x64\ReleaseSM61\VanitySearch.exe` (для ReleaseSM61)
- `x64\Release\VanitySearch.exe` (для Release)

### 0.4 Сборка из консоли (MSBuild)

В PowerShell:

```powershell
Set-Location "C:\path\to\MyWalletSearch"
$msb = "C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe"

# GTX 1050 Ti / CUDA 11.8 / sm_61
& $msb VanitySearch.sln /t:Rebuild /p:Configuration=ReleaseSM61 /p:Platform=x64 /m /v:m
```

### 0.5 Запуск exe + сохранение лога

```powershell
Set-Location "C:\path\to\MyWalletSearch\x64\ReleaseSM61"

# список CUDA-устройств (встроенная проверка, что runtime ок)
.\VanitySearch.exe -l

# любой запуск с записью лога в файл:
.\VanitySearch.exe -gpu -gpuId 0 -g 48,128 -t 2 "1*1"  *> run.log
```

> `*>` в PowerShell пишет и stdout, и stderr в один файл.

### 0.6 Как выбрать grid (`-g`) на Windows

Формула по подсказке `-h`: **дефолт = `8*(MP),128`**, где MP = число SM (multiprocessors).

Узнать MP можно командой:

```powershell
.\VanitySearch.exe -l
```

Пример для GTX 1050 Ti (6 SM):
- **`-g 48,128`**

Рекомендация:
- Начинайте с дефолта (`8*MP,128`), и при OOM уменьшайте X (`48` → `32` → `16`).

### 0.7 Проверка корректности GPU/CPU (`-check`)

Важно: **`-g` должен быть ДО `-check`**, иначе `-g` не применится.

```powershell
Set-Location "C:\path\to\MyWalletSearch\x64\ReleaseSM61"
.\VanitySearch.exe -gpu -gpuId 0 -g 48,128 -m 4096 -check  *> check.log
```

Ожидаемо в конце:
- `GPU/CPU check OK`

### 0.8 Сегментный тест + префикс*суффикс (Windows пример)

Скопируйте тестовый конфиг сегментов рядом с exe (если он лежит в корне репо):

```powershell
Copy-Item -Force "C:\path\to\MyWalletSearch\seg_matrix_test.txt" "C:\path\to\MyWalletSearch\x64\ReleaseSM61\seg_matrix_test.txt"
```

Запуск (быстрый тест на маленьком диапазоне, чтобы быстро увидеть Found):

```powershell
Set-Location "C:\path\to\MyWalletSearch\x64\ReleaseSM61"
.\VanitySearch.exe `
  -seg .\seg_matrix_test.txt -bits 24 `
  -gpu -gpuId 0 -g 48,128 -t 2 -m 200000 `
  -stop -o out_seg_prefix_suffix.txt `
  "1уц*"  *> seg_test.log
```

- Результаты (адреса/ключи) будут в `out_seg_prefix_suffix.txt`
- Лог — в `seg_test.log`

### 0.9 Остановка зависшего процесса (Windows)

Если нужно быстро остановить:

```powershell
Get-Process VanitySearch -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 0.10 (Опционально) GUI-лаунчер для Windows

В репозитории есть мини-приложение `vanity_gui.py` (tkinter, без зависимостей), которое умеет:
- генерировать seg-файл из многострочного поля
- запускать `VanitySearch.exe` с `-progress/-autosave` (и `-resume`, если progress уже существует)
- писать лог/прогресс/найденные в файлы с суффиксами от одного базового имени
- показывать tail последних N строк лога и вывод `show_segment_progress.py`
- останавливать все процессы `VanitySearch.exe`
- пересобирать `VanitySearch` под текущий GPU (через MSBuild)

Запуск:

```powershell
cd C:\path\to\MyWalletSearch
python .\vanity_gui.py
```

Файлы создаются в `runs\` с именованием как в `run_puzzle71_69_72.sh`:
- `seg_<base>.txt`
- `progress_<base>.dat`
- `out_<base>.txt`
- `log_<base>.log`

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


