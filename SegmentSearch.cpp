/*
 * Segment Search Extension for VanitySearch
 * Реализация сегментированного поиска
 */

#include "SegmentSearch.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#ifndef WIN64
#include <pthread.h>
#else
#include <windows.h>
#endif

SegmentSearch::SegmentSearch() {
  bitRange = 0;
  activeSegments = 0;
  progressManager = NULL;
  progressSavingEnabled = false;
  keysCheckedSinceLastSave = 0;
  loadBalancer = NULL;
  loadBalancingEnabled = false;
  searchAlgorithm = ALGORITHM_STANDARD;  // По умолчанию стандартный
  kangarooSearch = NULL;
#ifndef WIN64
  pthread_mutex_init(&mutex, NULL);
#else
  mutex = CreateMutex(NULL, FALSE, NULL);
#endif
}

SegmentSearch::~SegmentSearch() {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  segments.clear();
  if (progressManager != NULL) {
    delete progressManager;
    progressManager = NULL;
  }
  if (loadBalancer != NULL) {
    delete loadBalancer;
    loadBalancer = NULL;
  }
  if (kangarooSearch != NULL) {
    delete kangarooSearch;
    kangarooSearch = NULL;
  }
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
  pthread_mutex_destroy(&mutex);
#else
  ReleaseMutex(mutex);
  CloseHandle(mutex);
#endif
}

void SegmentSearch::AddSegment(double startPercent, double endPercent, 
                                SearchDirection direction, const std::string &name) {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  SearchSegment seg;
  seg.startPercent = startPercent;
  seg.endPercent = endPercent;
  seg.direction = direction;
  seg.active = true;
  seg.name = name.empty() ? "Segment_" + std::to_string(segments.size() + 1) : name;
  
  segments.push_back(seg);
  activeSegments++;
  
  std::string segName = seg.name;
  std::string dirStr = (direction == DIRECTION_UP ? "ВВЕРХ" : "ВНИЗ");
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  printf("[SegmentSearch] Добавлен сегмент: %s (%.2f%% -> %.2f%%, направление: %s)\n",
         segName.c_str(), startPercent, endPercent, dirStr.c_str());
}

bool SegmentSearch::LoadSegmentsFromFile(const std::string &filename) {
  std::ifstream file(filename);
  if (!file.is_open()) {
    printf("[SegmentSearch] Ошибка: не удалось открыть файл %s\n", filename.c_str());
    return false;
  }
  
  std::string line;
  int lineNum = 0;
  
  printf("[SegmentSearch] Загрузка конфигурации из %s\n", filename.c_str());
  
  while (std::getline(file, line)) {
    lineNum++;
    
    // Пропустить пустые строки и комментарии
    if (line.empty() || line[0] == '#' || line[0] == ';') {
      continue;
    }
    
    // Формат: startPercent endPercent direction [name]
    // Пример: 45.0 54.0 up segment1
    // Пример: 59.0 54.0 down segment2
    
    std::istringstream iss(line);
    double start, end;
    std::string dirStr, name;
    
    if (!(iss >> start >> end >> dirStr)) {
      printf("[SegmentSearch] Предупреждение: неверный формат строки %d, пропускаем\n", lineNum);
      continue;
    }
    
    // Прочитать имя (опционально)
    iss >> name;
    if (name.empty()) {
      name = "Line_" + std::to_string(lineNum);
    }
    
    // Определить направление
    SearchDirection dir;
    std::transform(dirStr.begin(), dirStr.end(), dirStr.begin(), ::tolower);
    if (dirStr == "up" || dirStr == "вверх") {
      dir = DIRECTION_UP;
    } else if (dirStr == "down" || dirStr == "вниз") {
      dir = DIRECTION_DOWN;
    } else {
      printf("[SegmentSearch] Предупреждение: неизвестное направление '%s' в строке %d, используем UP\n", 
             dirStr.c_str(), lineNum);
      dir = DIRECTION_UP;
    }
    
    // Проверка диапазона
    if (start < 0.0 || start > 100.0 || end < 0.0 || end > 100.0) {
      printf("[SegmentSearch] Предупреждение: проценты вне диапазона 0-100 в строке %d, пропускаем\n", lineNum);
      continue;
    }
    
    AddSegment(start, end, dir, name);
  }
  
  file.close();
  
  printf("[SegmentSearch] Загружено сегментов: %d\n", (int)segments.size());
  return segments.size() > 0;
}

void SegmentSearch::CalculateKeyAtPercent(double percent, Int &result) {
  // result = fullRangeStart + (fullRangeSize * percent / 100.0)
  
  Int offset;
  offset.Set(&fullRangeSize);
  
  // Умножаем на процент (используем целочисленную арифметику)
  // Умножаем на percent*1000000 и делим на 100000000 для точности
  uint64_t percentScaled = (uint64_t)(percent * 1000000.0);
  offset.Mult(percentScaled);
  
  // Делим на 100 * 1000000
  Int divisor((uint64_t)100000000);
  offset.Div(&divisor);
  
  result.Set(&fullRangeStart);
  result.Add(&offset);
}

void SegmentSearch::InitializeSegments(int bits) {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  bitRange = bits;
  
  // Вычислить полный диапазон для заданного количества бит
  // Для puzzle 71: диапазон от 2^70 до 2^71-1
  
  fullRangeStart.SetInt32(1);
  fullRangeStart.ShiftL(bits - 1);  // 2^(bits-1)
  
  fullRangeEnd.SetInt32(1);
  fullRangeEnd.ShiftL(bits);        // 2^bits
  fullRangeEnd.SubOne();            // 2^bits - 1
  
  fullRangeSize.Set(&fullRangeEnd);
  fullRangeSize.Sub(&fullRangeStart);
  fullRangeSize.AddOne();
  
  std::string startStr = fullRangeStart.GetBase16();
  std::string endStr = fullRangeEnd.GetBase16();
  
  // Вычислить границы для каждого сегмента
  std::vector<std::string> segNames;
  std::vector<std::string> segStartStrs;
  std::vector<std::string> segEndStrs;
  
  for (size_t i = 0; i < segments.size(); i++) {
    CalculateKeyAtPercent(segments[i].startPercent, segments[i].rangeStart);
    CalculateKeyAtPercent(segments[i].endPercent, segments[i].rangeEnd);
    
    // Установить начальную позицию в зависимости от направления
    if (segments[i].direction == DIRECTION_UP) {
      segments[i].currentKey.Set(&segments[i].rangeStart);
    } else {
      segments[i].currentKey.Set(&segments[i].rangeEnd);
    }
    
    segNames.push_back(segments[i].name);
    segStartStrs.push_back(segments[i].rangeStart.GetBase16());
    segEndStrs.push_back(segments[i].rangeEnd.GetBase16());
  }
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  printf("[SegmentSearch] Инициализация для %d-битного диапазона\n", bits);
  printf("[SegmentSearch] Диапазон: %s\n", startStr.c_str());
  printf("[SegmentSearch]      до: %s\n", endStr.c_str());
  
  for (size_t i = 0; i < segNames.size(); i++) {
    printf("[SegmentSearch] %s: %s -> %s\n", 
           segNames[i].c_str(),
           segStartStrs[i].c_str(),
           segEndStrs[i].c_str());
  }
}

int SegmentSearch::GetActiveSegmentCount() const {
#ifndef WIN64
  pthread_mutex_lock((pthread_mutex_t*)&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  int count = activeSegments;
  
#ifndef WIN64
  pthread_mutex_unlock((pthread_mutex_t*)&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  return count;
}

int SegmentSearch::GetSegmentForThread(int threadId) {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  if (segments.empty()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return -1;
  }
  
  // Использовать балансировщик, если включен
  if (loadBalancingEnabled && loadBalancer != NULL) {
    int seg = loadBalancer->GetSegmentForThread(threadId);
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return seg;
  }
  
  // Простое распределение: round-robin по активным сегментам
  int activeCount = 0;
  int activeSegCount = activeSegments;
  for (size_t i = 0; i < segments.size(); i++) {
    if (segments[i].active) {
      if (activeCount == (threadId % activeSegCount)) {
#ifndef WIN64
        pthread_mutex_unlock(&mutex);
#else
        ReleaseMutex(mutex);
#endif
        return i;
      }
      activeCount++;
    }
  }
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  return 0; // Fallback
}

bool SegmentSearch::GetStartingKey(int threadId, Int &key) {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  int segIdx = -1;
  if (segments.empty()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return false;
  }
  
  // Использовать балансировщик, если включен
  if (loadBalancingEnabled && loadBalancer != NULL) {
    segIdx = loadBalancer->GetSegmentForThread(threadId);
  } else {
    // Простое распределение: round-robin по активным сегментам
    int activeCount = 0;
    int activeSegCount = activeSegments;
    for (size_t i = 0; i < segments.size(); i++) {
      if (segments[i].active) {
        if (activeCount == (threadId % activeSegCount)) {
          segIdx = i;
          break;
        }
        activeCount++;
      }
    }
    if (segIdx < 0) segIdx = 0;
  }
  
  if (segIdx < 0 || segIdx >= (int)segments.size()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return false;
  }
  
  SearchSegment &seg = segments[segIdx];
  if (!seg.active) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return false;
  }
  
  key.Set(&seg.currentKey);
  
  // Добавляем смещение для потока, чтобы потоки не искали в одном месте
  Int offset((int64_t)threadId);
  offset.ShiftL(32);  // Смещение на основе ID потока
  key.Add(&offset);
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  return true;
}

bool SegmentSearch::GetNextKey(int threadId, Int &key) {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  int segIdx = -1;
  if (segments.empty()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return false;
  }
  
  // Использовать балансировщик, если включен
  if (loadBalancingEnabled && loadBalancer != NULL) {
    segIdx = loadBalancer->GetSegmentForThread(threadId);
  } else {
    // Простое распределение: round-robin по активным сегментам
    int activeCount = 0;
    int activeSegCount = activeSegments;
    for (size_t i = 0; i < segments.size(); i++) {
      if (segments[i].active) {
        if (activeCount == (threadId % activeSegCount)) {
          segIdx = i;
          break;
        }
        activeCount++;
      }
    }
    if (segIdx < 0) segIdx = 0;
  }
  
  if (segIdx < 0 || segIdx >= (int)segments.size()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return false;
  }
  
  SearchSegment &seg = segments[segIdx];
  if (!seg.active) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return false;
  }
  
  // Проверить, не вышли ли за пределы сегмента
  if (seg.direction == DIRECTION_UP) {
    if (seg.currentKey.IsGreater(&seg.rangeEnd)) {
      seg.active = false;
      activeSegments--;
      std::string segName = seg.name;
#ifndef WIN64
      pthread_mutex_unlock(&mutex);
#else
      ReleaseMutex(mutex);
#endif
      printf("[SegmentSearch] Сегмент %s завершен (поиск вверх)\n", segName.c_str());
      return false;
    }
  } else {
    if (seg.currentKey.IsLower(&seg.rangeStart)) {
      seg.active = false;
      activeSegments--;
      std::string segName = seg.name;
#ifndef WIN64
      pthread_mutex_unlock(&mutex);
#else
      ReleaseMutex(mutex);
#endif
      printf("[SegmentSearch] Сегмент %s завершен (поиск вниз)\n", segName.c_str());
      return false;
    }
  }
  
  key.Set(&seg.currentKey);
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  return true;
}

bool SegmentSearch::IsSearchComplete() {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  bool complete = (activeSegments == 0);
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  return complete;
}

void SegmentSearch::PrintSegments() {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  int segCount = segments.size();
  int activeCount = activeSegments;
  int bitR = bitRange;
  
  std::vector<std::string> segNames;
  std::vector<double> startPercents;
  std::vector<double> endPercents;
  std::vector<std::string> directions;
  std::vector<bool> actives;
  std::vector<std::string> startStrs;
  std::vector<std::string> endStrs;
  
  for (size_t i = 0; i < segments.size(); i++) {
    const SearchSegment &seg = segments[i];
    segNames.push_back(seg.name);
    startPercents.push_back(seg.startPercent);
    endPercents.push_back(seg.endPercent);
    directions.push_back(seg.direction == DIRECTION_UP ? "ВВЕРХ ↑" : "ВНИЗ ↓");
    actives.push_back(seg.active);
    Int tmp1, tmp2;
    tmp1.Set((Int*)&seg.rangeStart);
    tmp2.Set((Int*)&seg.rangeEnd);
    startStrs.push_back(tmp1.GetBase16());
    endStrs.push_back(tmp2.GetBase16());
  }
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  printf("\n=== Конфигурация сегментов поиска ===\n");
  printf("Всего сегментов: %d\n", segCount);
  printf("Активных сегментов: %d\n", activeCount);
  printf("Битовый диапазон: %d\n\n", bitR);
  
  for (size_t i = 0; i < segNames.size(); i++) {
    printf("Сегмент %zu: %s\n", i + 1, segNames[i].c_str());
    printf("  Диапазон: %.2f%% -> %.2f%%\n", startPercents[i], endPercents[i]);
    printf("  Направление: %s\n", directions[i].c_str());
    printf("  Статус: %s\n", actives[i] ? "Активен" : "Завершен");
    printf("  Начало: %s\n", startStrs[i].c_str());
    printf("  Конец:  %s\n", endStrs[i].c_str());
    printf("\n");
  }
  
  printf("=====================================\n\n");
}

double SegmentSearch::GetOverallProgress() {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  if (segments.empty()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return 0.0;
  }
  
  double totalProgress = 0.0;
  for (size_t i = 0; i < segments.size(); i++) {
    const SearchSegment &seg = segments[i];
    
    if (!seg.active) {
      totalProgress += 100.0;
      continue;
    }
    
    // Вычислить прогресс в текущем сегменте
    Int segSize;
    Int temp1, temp2, temp3;
    temp1.Set((Int*)&seg.rangeEnd);
    temp2.Set((Int*)&seg.rangeStart);
    temp3.Set((Int*)&seg.currentKey);
    
    if (temp1.IsGreater(&temp2)) {
      segSize.Set(&temp1);
      segSize.Sub(&temp2);
    } else {
      segSize.Set(&temp2);
      segSize.Sub(&temp1);
    }
    
    Int progress;
    if (seg.direction == DIRECTION_UP) {
      progress.Set(&temp3);
      progress.Sub(&temp2);
    } else {
      progress.Set(&temp1);
      progress.Sub(&temp3);
    }
    
    double segProgress = 0.0;
    if (!segSize.IsZero()) {
      segProgress = (progress.ToDouble() / segSize.ToDouble()) * 100.0;
    }
    
    totalProgress += segProgress;
  }
  
  double result = totalProgress / segments.size();
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  return result;
}

void SegmentSearch::EnableProgressSaving(const std::string &progressFile, int autoSaveInterval) {
  if (progressManager == NULL) {
    progressManager = new ProgressManager();
  }
  
  progressManager->SetProgressFile(progressFile);
  progressManager->EnableAutoSave(autoSaveInterval);
  progressSavingEnabled = true;
  
  printf("[SegmentSearch] Сохранение прогресса включено: %s\n", progressFile.c_str());
}

bool SegmentSearch::SaveProgress(const std::string &targetAddress) {
  if (!progressSavingEnabled || progressManager == NULL) {
    return false;
  }
  
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  // Инициализация прогресса при первом сохранении
  if (currentProgress.segments.empty() && !segments.empty()) {
    currentProgress = progressManager->CreateProgress(bitRange, targetAddress);
  }
  
  ExportToProgress();  // Уже защищен мьютексом внутри
  currentProgress.targetAddress = targetAddress;
  currentProgress.lastSaveTime = time(NULL);
  
  SearchProgress progressCopy = currentProgress;
  uint64_t keysSinceSave = keysCheckedSinceLastSave;
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  bool result = progressManager->SaveProgress(progressCopy);
  if (result) {
    progressManager->MarkSaved();
#ifndef WIN64
    pthread_mutex_lock(&mutex);
#else
    WaitForSingleObject(mutex, INFINITE);
#endif
    keysCheckedSinceLastSave = 0;
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
  }
  
  return result;
}

bool SegmentSearch::LoadProgress(const std::string &targetAddress) {
  if (progressManager == NULL) {
    progressManager = new ProgressManager();
  }
  
  if (!progressManager->ProgressFileExists()) {
    printf("[SegmentSearch] Файл прогресса не найден, начинаем с нуля\n");
    return false;
  }
  
  SearchProgress loadedProgress;
  if (!progressManager->LoadProgress(loadedProgress)) {
    return false;
  }
  
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  // Проверка соответствия адреса
  if (!targetAddress.empty() && loadedProgress.targetAddress != targetAddress) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    printf("[SegmentSearch] Предупреждение: целевой адрес не совпадает\n");
    printf("  В файле: %s\n", loadedProgress.targetAddress.c_str());
    printf("  Запрошен: %s\n", targetAddress.c_str());
    printf("  Игнорируем файл прогресса\n");
    return false;
  }
  
  // Проверка битового диапазона
  if (loadedProgress.bitRange != bitRange) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    printf("[SegmentSearch] Предупреждение: битовый диапазон не совпадает (%d vs %d)\n",
           loadedProgress.bitRange, bitRange);
    return false;
  }
  
  currentProgress = loadedProgress;
  
  // Импорт сегментов из прогресса
  ImportFromProgress();  // Уже защищен мьютексом внутри
  
  std::string stats = progressManager->GetProgressStats(currentProgress);
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  printf("[SegmentSearch] ✓ Прогресс восстановлен успешно\n");
  printf("%s", stats.c_str());
  
  return true;
}

void SegmentSearch::UpdateProgress(int threadId, uint64_t keysChecked) {
  if (!progressSavingEnabled) return;
  
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  int segIdx = -1;
  if (!segments.empty()) {
    // Использовать балансировщик, если включен
    if (loadBalancingEnabled && loadBalancer != NULL) {
      segIdx = loadBalancer->GetSegmentForThread(threadId);
    } else {
      // Простое распределение: round-robin по активным сегментам
      int activeCount = 0;
      int activeSegCount = activeSegments;
      for (size_t i = 0; i < segments.size(); i++) {
        if (segments[i].active) {
          if (activeCount == (threadId % activeSegCount)) {
            segIdx = i;
            break;
          }
          activeCount++;
        }
      }
      if (segIdx < 0) segIdx = 0;
    }
  }
  
  if (segIdx >= 0 && segIdx < (int)segments.size()) {
    ProgressManager::UpdateSegmentProgress(currentProgress, segIdx, 
                                            segments[segIdx].currentKey, keysChecked);
    keysCheckedSinceLastSave += keysChecked;
    
    // Периодический вывод прогресса (каждые 1M ключей)
    static uint64_t lastLogProgress = 0;
    if (currentProgress.totalKeysChecked - lastLogProgress >= 1000000) {
      printf("[ProgressManager] Всего ключей проверено: %llu (сегмент %d: %llu)\n",
             (unsigned long long)currentProgress.totalKeysChecked,
             segIdx,
             (unsigned long long)currentProgress.segments[segIdx].keysChecked);
      lastLogProgress = currentProgress.totalKeysChecked;
    }
    
    // Автосохранение
    bool shouldSave = ShouldAutoSave();
    std::string targetAddr = currentProgress.targetAddress;
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    
    if (shouldSave) {
      SaveProgress(targetAddr);
    }
  } else {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
  }
}

void SegmentSearch::UpdateKangarooProgress(int segmentIndex, uint64_t totalJumps) {
  if (!progressSavingEnabled) return;
  
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  if (segmentIndex < 0 || segmentIndex >= (int)segments.size()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return;
  }
  
  // Для Kangaroo используем jumps как эквивалент ключей
  // 1 jump ≈ проверка одного ключа в контексте прогресса
  uint64_t keysEquivalent = totalJumps;
  
  // Получаем текущее значение из прогресса
  uint64_t oldKeys = 0;
  if (segmentIndex < (int)currentProgress.segments.size()) {
    oldKeys = currentProgress.segments[segmentIndex].keysChecked;
  }
  
  // Обновляем только если есть прирост
  if (keysEquivalent > oldKeys) {
    uint64_t increment = keysEquivalent - oldKeys;
    ProgressManager::UpdateSegmentProgress(currentProgress, segmentIndex,
                                            segments[segmentIndex].currentKey, increment);
    keysCheckedSinceLastSave += increment;
    
    std::string segName = segments[segmentIndex].name;
    std::string targetAddr = currentProgress.targetAddress;
    bool shouldSave = ShouldAutoSave();  // Уже защищен мьютексом внутри
    
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    
    // Периодический вывод прогресса (каждые 1M jumps)
    static uint64_t lastLogJumps = 0;
    if (totalJumps - lastLogJumps >= 1000000) {
      printf("[ProgressManager] Kangaroo: %llu jumps (сегмент %d: %s)\n",
             (unsigned long long)totalJumps,
             segmentIndex,
             segName.c_str());
      lastLogJumps = totalJumps;
    }
    
    // Автосохранение
    if (shouldSave) {
      SaveProgress(targetAddr);
    }
  } else {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
  }
}

bool SegmentSearch::ShouldAutoSave() {
  if (!progressSavingEnabled || progressManager == NULL) {
    return false;
  }
  
  // progressManager->ShouldSave() не требует синхронизации,
  // так как он использует только внутренние переменные времени
  return progressManager->ShouldSave();
}

void SegmentSearch::ExportToProgress() {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  currentProgress.bitRange = bitRange;
  // НЕ очищаем segments - сохраняем существующие значения keysChecked
  // Обновляем только изменяемые поля
  for (size_t i = 0; i < segments.size(); i++) {
    if (i < currentProgress.segments.size()) {
      // Обновляем существующий сегмент
      currentProgress.segments[i].currentKey = segments[i].currentKey.GetBase16();
      currentProgress.segments[i].active = segments[i].active;
      currentProgress.segments[i].lastUpdate = time(NULL);
      // keysChecked сохраняем из текущего прогресса (не сбрасываем!)
    } else {
      // Создаем новый сегмент
      SegmentProgress sp;
      sp.name = segments[i].name;
      sp.startPercent = segments[i].startPercent;
      sp.endPercent = segments[i].endPercent;
      sp.direction = (segments[i].direction == DIRECTION_UP) ? 0 : 1;
      sp.currentKey = segments[i].currentKey.GetBase16();
      sp.active = segments[i].active;
      sp.keysChecked = 0;  // Только для новых сегментов
      sp.lastUpdate = time(NULL);
      currentProgress.segments.push_back(sp);
    }
  }
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
}

void SegmentSearch::ImportFromProgress() {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  if (currentProgress.segments.size() != segments.size()) {
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    printf("[SegmentSearch] Предупреждение: количество сегментов не совпадает\n");
    return;
  }
  
  std::vector<std::string> segNames;
  std::vector<uint64_t> keysChecked;
  
  for (size_t i = 0; i < segments.size() && i < currentProgress.segments.size(); i++) {
    const SegmentProgress &sp = currentProgress.segments[i];
    
    // Восстанавливаем текущий ключ
    segments[i].currentKey.SetBase16((char *)sp.currentKey.c_str());
    segments[i].active = sp.active;
    
    segNames.push_back(sp.name);
    keysChecked.push_back(sp.keysChecked);
  }
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  for (size_t i = 0; i < segNames.size(); i++) {
    printf("[SegmentSearch] Восстановлен сегмент %s: %llu ключей проверено\n",
           segNames[i].c_str(), (unsigned long long)keysChecked[i]);
  }
}

void SegmentSearch::EnableLoadBalancing(int numThreads, int rebalanceInterval) {
  if (loadBalancer == NULL) {
    loadBalancer = new LoadBalancer();
  }
  
  loadBalancer->Initialize(segments.size(), numThreads);
  loadBalancer->SetRebalanceInterval(rebalanceInterval);
  loadBalancer->EnableAdaptiveBalancing(true);
  loadBalancingEnabled = true;
  
  printf("[SegmentSearch] Балансировка нагрузки включена\n");
}

void SegmentSearch::UpdateLoadStats(int threadId, uint64_t keysChecked, double keysPerSecond) {
  if (!loadBalancingEnabled || loadBalancer == NULL) return;
  
  int segId = GetSegmentForThread(threadId);
  if (segId >= 0 && segId < (int)segments.size()) {
    loadBalancer->UpdateSegmentStats(segId, keysChecked, keysPerSecond);
  }
}

bool SegmentSearch::PerformRebalance() {
  if (!loadBalancingEnabled || loadBalancer == NULL) {
    return false;
  }
  
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  // Обновить статус завершённых сегментов
  for (size_t i = 0; i < segments.size(); i++) {
    if (!segments[i].active) {
      loadBalancer->MarkSegmentCompleted(i);
    }
  }
  
  bool result = loadBalancer->Rebalance();
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  return result;
}

void SegmentSearch::SetSearchAlgorithm(SearchAlgorithm algorithm) {
  searchAlgorithm = algorithm;
  
  if (algorithm == ALGORITHM_KANGAROO) {
    printf("[SegmentSearch] Алгоритм поиска: Pollard's Kangaroo 🦘\n");
    printf("[SegmentSearch] Теоретическая сложность: O(sqrt(N))\n");
    printf("[SegmentSearch] Ожидаемое ускорение: до 2^35x\n");
  } else {
    printf("[SegmentSearch] Алгоритм поиска: Стандартный линейный\n");
  }
}

bool SegmentSearch::SearchSegmentWithKangaroo(int segmentIndex, Secp256K1 *secp,
                                                const Point &targetPubKey, Int &foundKey) {
  if (segmentIndex < 0 || segmentIndex >= (int)segments.size()) {
    return false;
  }
  
  const SearchSegment &seg = segments[segmentIndex];
  
  printf("\n[Kangaroo] Поиск в сегменте: %s\n", seg.name.c_str());
  printf("[Kangaroo] Диапазон: %.2f%% - %.2f%%\n", seg.startPercent, seg.endPercent);
  
  // Создать Kangaroo search для этого сегмента
  if (kangarooSearch == NULL) {
    kangarooSearch = new KangarooSearch(secp);
  }
  
  // Инициализировать для диапазона сегмента
  kangarooSearch->Initialize(seg.rangeStart, seg.rangeEnd, targetPubKey);
  
  // Настроить параметры
  kangarooSearch->SetNumKangaroos(4, 4);  // 4 tame, 4 wild
  
  // Периодическое обновление прогресса
  time_t lastProgressUpdate = time(NULL);
  uint64_t lastJumps = 0;
  
  // Запустить поиск с периодическим обновлением прогресса
  // Модифицируем Search чтобы он периодически обновлял прогресс
  // Для этого нужно добавить callback или периодически проверять totalJumps
  
  // Запустить поиск
  bool found = kangarooSearch->Search(foundKey, 0);  // 0 = без лимита
  
  // Обновить прогресс после завершения
  if (kangarooSearch != NULL) {
    uint64_t totalJumps = kangarooSearch->GetTotalJumps();
    UpdateKangarooProgress(segmentIndex, totalJumps);
  }
  
  return found;
}

