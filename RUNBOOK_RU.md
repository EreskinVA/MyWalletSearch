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

## Что означают поля в найденном результате (out-файл)

Когда VanitySearch находит подходящий адрес, он пишет “блок” в `out_*.txt`.
Поля идут в порядке “сначала адрес → приватные ключи → позиция в puzzle → сегментная информация”.

### Адрес и приватный ключ

- **`PubAddress`**: найденный публичный адрес (то, что вы искали по паттерну).
- **`Priv (WIF)`**: приватный ключ в формате WIF (готов для импорта в кошелёк).
- **`Priv (HEX)` / `Priv (DEC)`**: тот же приватный ключ в hex/decimal.

Важно: `Priv` — это “реальный” приватный ключ, который соответствует адресу **после внутренних оптимизаций**
(эндоморфизм/симметрия, всё по модулю порядка кривой `secp256k1`).
Поэтому `Priv (DEC)` может быть “очень большим” (256-битное число) — это нормально.

### Позиция в Puzzle диапазоне (bits=N)

Эти поля отвечают на вопрос “где находится найденный ключ в пазле N”:

- **`PuzzleBits`**: значение `-bits`, например `71`.
- **`PuzzleStart (DEC)`**: нижняя граница puzzle-диапазона: \(2^{bits-1}\).
- **`PuzzlePos0 (DEC)`**: **порядковый номер (0-based)** в puzzle-диапазоне:
  \(PuzzlePos0 = PuzzleKeyAbs - 2^{bits-1}\).
- **`PuzzleKeyAbs (DEC/HEX)`**: абсолютный ключ в координатах puzzle:
  \(PuzzleKeyAbs = 2^{bits-1} + PuzzlePos0\).

`PuzzleKeyAbs` удобно сравнивать с сегментами типа `abs ...` (потому что это те же абсолютные числа).

### Сегментная информация (Segment Search)

Эти поля показывают “что именно перебирали” в рамках вашего сегментного диапазона:

- **`SegKey (DEC/HEX)`**: “сырой” ключ, который реально перебирался **внутри сегмента**
  (до endomorphism/симметрий). Именно он должен попадать в диапазон ваших `abs` сегментов.
- **`Segment`**: имя сегмента и его номер (например `cpu715_725_2 (#2)`).
- **`SegmentDir`**: направление сегмента (`UP`/`DOWN`).
- **`SegmentOffset (DEC)`**: смещение найденного `SegKey` от начала сегмента (в ключах).
- **`SegmentSize (DEC)`**: размер сегмента (в ключах).

Практический совет:
- если хотите “порядковый номер в puzzle” — смотрите **`PuzzlePos0 (DEC)`**
- если хотите проверить “попадает ли в abs-сегмент” — смотрите **`PuzzleKeyAbs (DEC)`** или **`SegKey (DEC)`**

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

### 4.1.1 Паттерны поиска: все варианты (prefix / wildcard / prefix*suffix / позиционная маска / -i)

`VanitySearch` принимает **один позиционный аргумент** (последний) — `prefix`, который может быть:
- простым префиксом (самый быстрый режим)
- wildcard-шаблоном с `*` и `?`
- формой `prefix*suffix`
- “позиционной маской” (полноразмерный шаблон 26..35 символов со `*`)

Важно:
- если в паттерне есть `*` или `?`, всегда берите его в кавычки: `"1P*X"`, иначе shell может попытаться развернуть `*` как glob.
- паттерн **должен быть последним аргументом** (после всех `-seg/-bits/-gpu/...`), иначе будет `Unexpected ... argument`.

Рекомендации “как лучше”
- Не смешивай в одном файле очень “широкие” (1P*X, 1PWo3J*) и “узкие” (1PWo3JeB9jr) широкие будут забивать буфер находок и замедлять всё.
- Для GPU при широких паттернах заранее ставь больше -m или уменьшай -g, иначе увидишь items lost.
- Если хочешь “остановиться когда всё найдено”, добавляй -stop — он остановит, когда каждый паттерн найдёт хотя бы одно совпадение.

Создание файла для нескольких паттернов patterns.txt
  Пример:
```
18ss
1PWo3J???
1PWo3JeB
1ABC*XYZ
1P*X
```
Правила:
- не ставь кавычки в файле (пиши просто 1P*X, 1PWo3J???).
- строки с * и ? в файле безопасны — shell их не трогает.

#### A) Простой префикс (без `*` и `?`)

```bash
./VanitySearch -t 4 -o out.txt 18ss
```

#### B) Wildcard: `*` (любая последовательность) и `?` (один символ)

```bash
# '*' = любая последовательность
./VanitySearch -t 4 -o out.txt "1P*X"

# '?' = ровно один символ
./VanitySearch -t 4 -o out.txt "1PWo3J????"
```

#### C) Префикс + суффикс: `prefix*suffix`

```bash
./VanitySearch -t 4 -o out.txt "1ABC*XYZ"
```

#### D) Позиционная маска (полноразмерный шаблон 26..35 символов)

Если задать паттерн длиной как у Base58 адреса (обычно 26..35) и использовать `*` как плейсхолдер
по позициям, движок включает ранний фильтр по фиксированным позициям (часто быстрее, чем обычный wildcard).

```bash
./VanitySearch -t 4 -o out.txt "1PW***e**j*G**********4C*as*****XU"
```

#### E) Несколько паттернов за один запуск: `-i inputfile`

Файл `patterns.txt` (по одному паттерну на строку):

```txt
18ss
1P*X
1ABC*XYZ
1PWo3JeB?????
```

Запуск:

```bash
./VanitySearch -t 4 -i patterns.txt -o out.txt
```

#### F) Case-insensitive: `-c`

```bash
./VanitySearch -c -t 4 -o out.txt "1PWo3J"
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

Поддерживаются **2 режима задания диапазона**:
- **проценты** (0..100) относительно выбранного `-bits` (например `71` для puzzle71)
- **ABS** (абсолютные значения приватного ключа) в **десятичном** или **hex** виде

Также поддерживается **приоритет** сегмента (`priority`, целое число `>=1`): влияет на распределение потоков (сегменты с большим приоритетом получают больше “веса”).

Чтобы не было неоднозначности (например `10 80 up` может быть и проценты, и десятичные ключи), рекомендуется использовать **явные префиксы режимов**:
- `pct` — проценты
- `abs` / `dec` — абсолютный диапазон в десятичном виде
- `key` / `0x...` — абсолютный диапазон в hex виде

Формат строки:
- **проценты**:
  - `pct <startPercent> <endPercent> <up|down> <name> [priority]`
  - или “старый” формат без `pct`: `<startPercent> <endPercent> <up|down> [name]` (не рекомендуется из-за неоднозначности)
- **ABS**:
  - `abs <startDec> <endDec> <up|down> <name> [priority]`
  - `dec <startDec> <endDec> <up|down> <name> [priority]`
  - `key <startHex> <endHex> <up|down> <name> [priority]` (hex может быть `0x...`)

**direction:**
- `up` — поиск от `start` к `end` (вверх, `start < end`)
- `down` — поиск от `start` к `end` (вниз, `start > end` для процентов и для ABS)

> Для `down` важно: **старт должен быть “сверху”**, финиш — “снизу”.  
> Пример: `pct 72.5 71.5 down ...` или `abs 2036520... 2024714... down ...`

#### 5.1.1 Примеры: проценты + направление + priority

```txt
# 2 сегмента в процентах, разные направления и приоритеты
pct 71.5000 71.7500 up   p715_1 1
pct 71.7500 71.5000 down p715_2 3
```

#### 5.1.2 Примеры: ABS (десятичные) + направление + priority

```txt
# ABS диапазон (decimal). name обязателен, priority опционален.
abs 2024714629530360385372 2025206542705659306749 up   cpu715_725_1 1
abs 2025206542705659306749 2025698455880958228126 up   cpu715_725_2 1
abs 2036520545737534498406 2036028632562235577030 down cpu715_725_back 2
```

#### 5.1.3 Примеры: ABS (hex) + направление + priority

```txt
# ABS диапазон (hex). Можно писать с 0x.
key 0x6DC28F5C28F5C28F5C 0x6DC962FC962FC962FD up   hex_1 1
key 0x6E6666666666666666 0x6E5F92C5F92C5F92C6 down hex_back 2
```

#### 5.1.4 Можно ли смешивать pct и abs в одном файле?

Да, можно. Рекомендуется всегда писать префикс `pct/abs/key`, чтобы парсер однозначно понял тип диапазона.

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


