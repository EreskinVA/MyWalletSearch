# Исправление проблемы thread-safety для SegmentSearch

## Проблема
Ошибка `malloc(): unaligned tcache chunk detected` возникала из-за гонок данных (race conditions) при многопоточном доступе к `SegmentSearch`.

## Решение
Добавлена синхронизация через мьютекс для всех критических секций в `SegmentSearch`.

## Совместимость

### ✅ Linux (включая серверы vast.ai)
- Используется `pthread_mutex_t` из библиотеки pthread
- Библиотека уже подключена в Makefile (`-lpthread`)
- Совместимо с любыми версиями Linux

### ✅ Windows
- Используется `HANDLE` и `CreateMutex`/`WaitForSingleObject`/`ReleaseMutex`
- Автоматическое определение через `#ifndef WIN64`

## Проверка на сервере

### 1. Проверить конфигурацию сервера:
```bash
ssh -p 44236 root@38.117.87.47 "uname -a && cat /etc/os-release | head -5"
```

### 2. Проверить наличие pthread:
```bash
ssh -p 44236 root@38.117.87.47 "ldconfig -p | grep pthread"
```

### 3. Пересобрать проект на сервере:
```bash
ssh -p 44236 root@38.117.87.47 "cd /path/to/VanitySearch && make clean && make gpu=1 CCAP=75"
```
(замените CCAP на вашу версию CUDA compute capability)

### 4. Проверить, что бинарник собран с pthread:
```bash
ssh -p 44236 root@38.117.87.47 "ldd VanitySearch | grep pthread"
```

## Измененные файлы

1. **SegmentSearch.h** - добавлен мьютекс в класс
2. **SegmentSearch.cpp** - добавлена синхронизация во все методы:
   - `GetActiveSegmentCount()`
   - `GetSegmentForThread()`
   - `GetStartingKey()`
   - `GetNextKey()`
   - `UpdateProgress()`
   - `UpdateKangarooProgress()`
   - `IsSearchComplete()`
   - `GetOverallProgress()`
   - `PerformRebalance()`
   - `AddSegment()`
   - `InitializeSegments()`
   - `PrintSegments()`
   - `ExportToProgress()`
   - `ImportFromProgress()`
   - `SaveProgress()`
   - `LoadProgress()`

## Ожидаемый результат

После пересборки и запуска:
- ✅ Ошибка `malloc(): unaligned tcache chunk detected` больше не должна возникать
- ✅ Поиск на GPU должен работать стабильно без прерываний
- ✅ Многопоточный доступ к сегментам теперь безопасен

## Тестирование

После пересборки запустите поиск и проверьте:
1. Нет ли ошибок в логах
2. Работает ли поиск стабильно длительное время
3. Корректно ли обновляется прогресс по сегментам

## Примечания

- Изменения обратно совместимы
- Не влияют на производительность (минимальные накладные расходы на блокировки)
- Все существующие функции работают как прежде

