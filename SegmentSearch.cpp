/*
 * Segment Search Extension for VanitySearch
 * Реализация сегментированного поиска
 */

#include "SegmentSearch.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>

SegmentSearch::SegmentSearch() {
  bitRange = 0;
  activeSegments = 0;
  progressManager = NULL;
  progressSavingEnabled = false;
  keysCheckedSinceLastSave = 0;
  loadBalancer = NULL;
  loadBalancingEnabled = false;
}

SegmentSearch::~SegmentSearch() {
  segments.clear();
  if (progressManager != NULL) {
    delete progressManager;
    progressManager = NULL;
  }
  if (loadBalancer != NULL) {
    delete loadBalancer;
    loadBalancer = NULL;
  }
}

void SegmentSearch::AddSegment(double startPercent, double endPercent, 
                                SearchDirection direction, const std::string &name) {
  SearchSegment seg;
  seg.startPercent = startPercent;
  seg.endPercent = endPercent;
  seg.direction = direction;
  seg.active = true;
  seg.name = name.empty() ? "Segment_" + std::to_string(segments.size() + 1) : name;
  
  segments.push_back(seg);
  activeSegments++;
  
  printf("[SegmentSearch] Добавлен сегмент: %s (%.2f%% -> %.2f%%, направление: %s)\n",
         seg.name.c_str(), startPercent, endPercent, 
         direction == DIRECTION_UP ? "ВВЕРХ" : "ВНИЗ");
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
  
  printf("[SegmentSearch] Инициализация для %d-битного диапазона\n", bits);
  printf("[SegmentSearch] Диапазон: %s\n", fullRangeStart.GetBase16().c_str());
  printf("[SegmentSearch]      до: %s\n", fullRangeEnd.GetBase16().c_str());
  
  // Вычислить границы для каждого сегмента
  for (size_t i = 0; i < segments.size(); i++) {
    CalculateKeyAtPercent(segments[i].startPercent, segments[i].rangeStart);
    CalculateKeyAtPercent(segments[i].endPercent, segments[i].rangeEnd);
    
    // Установить начальную позицию в зависимости от направления
    if (segments[i].direction == DIRECTION_UP) {
      segments[i].currentKey.Set(&segments[i].rangeStart);
    } else {
      segments[i].currentKey.Set(&segments[i].rangeEnd);
    }
    
    printf("[SegmentSearch] %s: %s -> %s\n", 
           segments[i].name.c_str(),
           segments[i].rangeStart.GetBase16().c_str(),
           segments[i].rangeEnd.GetBase16().c_str());
  }
}

int SegmentSearch::GetSegmentForThread(int threadId) {
  if (segments.empty()) return -1;
  
  // Использовать балансировщик, если включен
  if (loadBalancingEnabled && loadBalancer != NULL) {
    return loadBalancer->GetSegmentForThread(threadId);
  }
  
  // Простое распределение: round-robin по активным сегментам
  int activeCount = 0;
  for (size_t i = 0; i < segments.size(); i++) {
    if (segments[i].active) {
      if (activeCount == (threadId % GetActiveSegmentCount())) {
        return i;
      }
      activeCount++;
    }
  }
  
  return 0; // Fallback
}

bool SegmentSearch::GetStartingKey(int threadId, Int &key) {
  int segIdx = GetSegmentForThread(threadId);
  if (segIdx < 0 || segIdx >= (int)segments.size()) {
    return false;
  }
  
  SearchSegment &seg = segments[segIdx];
  if (!seg.active) {
    return false;
  }
  
  key.Set(&seg.currentKey);
  
  // Добавляем смещение для потока, чтобы потоки не искали в одном месте
  Int offset((int64_t)threadId);
  offset.ShiftL(32);  // Смещение на основе ID потока
  key.Add(&offset);
  
  return true;
}

bool SegmentSearch::GetNextKey(int threadId, Int &key) {
  int segIdx = GetSegmentForThread(threadId);
  if (segIdx < 0 || segIdx >= (int)segments.size()) {
    return false;
  }
  
  SearchSegment &seg = segments[segIdx];
  if (!seg.active) {
    return false;
  }
  
  // Проверить, не вышли ли за пределы сегмента
  if (seg.direction == DIRECTION_UP) {
    if (seg.currentKey.IsGreater(&seg.rangeEnd)) {
      seg.active = false;
      activeSegments--;
      printf("[SegmentSearch] Сегмент %s завершен (поиск вверх)\n", seg.name.c_str());
      return false;
    }
  } else {
    if (seg.currentKey.IsLower(&seg.rangeStart)) {
      seg.active = false;
      activeSegments--;
      printf("[SegmentSearch] Сегмент %s завершен (поиск вниз)\n", seg.name.c_str());
      return false;
    }
  }
  
  key.Set(&seg.currentKey);
  return true;
}

bool SegmentSearch::IsSearchComplete() {
  return activeSegments == 0;
}

void SegmentSearch::PrintSegments() {
  printf("\n=== Конфигурация сегментов поиска ===\n");
  printf("Всего сегментов: %d\n", (int)segments.size());
  printf("Активных сегментов: %d\n", activeSegments);
  printf("Битовый диапазон: %d\n\n", bitRange);
  
  for (size_t i = 0; i < segments.size(); i++) {
    const SearchSegment &seg = segments[i];
    printf("Сегмент %zu: %s\n", i + 1, seg.name.c_str());
    printf("  Диапазон: %.2f%% -> %.2f%%\n", seg.startPercent, seg.endPercent);
    printf("  Направление: %s\n", seg.direction == DIRECTION_UP ? "ВВЕРХ ↑" : "ВНИЗ ↓");
    printf("  Статус: %s\n", seg.active ? "Активен" : "Завершен");
    printf("  Начало: %s\n", seg.rangeStart.GetBase16().c_str());
    printf("  Конец:  %s\n", seg.rangeEnd.GetBase16().c_str());
    printf("\n");
  }
  
  printf("=====================================\n\n");
}

double SegmentSearch::GetOverallProgress() {
  if (segments.empty()) return 0.0;
  
  double totalProgress = 0.0;
  for (size_t i = 0; i < segments.size(); i++) {
    const SearchSegment &seg = segments[i];
    
    if (!seg.active) {
      totalProgress += 100.0;
      continue;
    }
    
    // Вычислить прогресс в текущем сегменте
    Int segSize;
    if (seg.rangeEnd.IsGreater(&seg.rangeStart)) {
      segSize.Set(&seg.rangeEnd);
      segSize.Sub(&seg.rangeStart);
    } else {
      segSize.Set(&seg.rangeStart);
      segSize.Sub(&seg.rangeEnd);
    }
    
    Int progress;
    if (seg.direction == DIRECTION_UP) {
      progress.Set(&seg.currentKey);
      progress.Sub(&seg.rangeStart);
    } else {
      progress.Set(&seg.rangeEnd);
      progress.Sub(&seg.currentKey);
    }
    
    double segProgress = 0.0;
    if (!segSize.IsZero()) {
      segProgress = (progress.ToDouble() / segSize.ToDouble()) * 100.0;
    }
    
    totalProgress += segProgress;
  }
  
  return totalProgress / segments.size();
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
  
  ExportToProgress();
  currentProgress.targetAddress = targetAddress;
  currentProgress.lastSaveTime = time(NULL);
  
  bool result = progressManager->SaveProgress(currentProgress);
  if (result) {
    progressManager->MarkSaved();
    keysCheckedSinceLastSave = 0;
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
  
  if (!progressManager->LoadProgress(currentProgress)) {
    return false;
  }
  
  // Проверка соответствия адреса
  if (!targetAddress.empty() && currentProgress.targetAddress != targetAddress) {
    printf("[SegmentSearch] Предупреждение: целевой адрес не совпадает\n");
    printf("  В файле: %s\n", currentProgress.targetAddress.c_str());
    printf("  Запрошен: %s\n", targetAddress.c_str());
    printf("  Игнорируем файл прогресса\n");
    return false;
  }
  
  // Проверка битового диапазона
  if (currentProgress.bitRange != bitRange) {
    printf("[SegmentSearch] Предупреждение: битовый диапазон не совпадает (%d vs %d)\n",
           currentProgress.bitRange, bitRange);
    return false;
  }
  
  // Импорт сегментов из прогресса
  ImportFromProgress();
  
  printf("[SegmentSearch] ✓ Прогресс восстановлен успешно\n");
  printf("%s", progressManager->GetProgressStats(currentProgress).c_str());
  
  return true;
}

void SegmentSearch::UpdateProgress(int threadId, uint64_t keysChecked) {
  if (!progressSavingEnabled) return;
  
  int segIdx = GetSegmentForThread(threadId);
  if (segIdx >= 0 && segIdx < (int)segments.size()) {
    ProgressManager::UpdateSegmentProgress(currentProgress, segIdx, 
                                            segments[segIdx].currentKey, keysChecked);
    keysCheckedSinceLastSave += keysChecked;
    
    // Автосохранение
    if (ShouldAutoSave()) {
      SaveProgress(currentProgress.targetAddress);
    }
  }
}

bool SegmentSearch::ShouldAutoSave() {
  if (!progressSavingEnabled || progressManager == NULL) {
    return false;
  }
  
  return progressManager->ShouldSave();
}

void SegmentSearch::ExportToProgress() {
  currentProgress.bitRange = bitRange;
  currentProgress.segments.clear();
  
  for (size_t i = 0; i < segments.size(); i++) {
    SegmentProgress sp;
    sp.name = segments[i].name;
    sp.startPercent = segments[i].startPercent;
    sp.endPercent = segments[i].endPercent;
    sp.direction = (segments[i].direction == DIRECTION_UP) ? 0 : 1;
    sp.currentKey = segments[i].currentKey.GetBase16();
    sp.active = segments[i].active;
    sp.keysChecked = 0;  // Будет обновлено при UpdateProgress
    sp.lastUpdate = time(NULL);
    
    currentProgress.segments.push_back(sp);
  }
}

void SegmentSearch::ImportFromProgress() {
  if (currentProgress.segments.size() != segments.size()) {
    printf("[SegmentSearch] Предупреждение: количество сегментов не совпадает\n");
    return;
  }
  
  for (size_t i = 0; i < segments.size() && i < currentProgress.segments.size(); i++) {
    const SegmentProgress &sp = currentProgress.segments[i];
    
    // Восстанавливаем текущий ключ
    segments[i].currentKey.SetBase16((char *)sp.currentKey.c_str());
    segments[i].active = sp.active;
    
    printf("[SegmentSearch] Восстановлен сегмент %s: %llu ключей проверено\n",
           sp.name.c_str(), (unsigned long long)sp.keysChecked);
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
  
  // Обновить статус завершённых сегментов
  for (size_t i = 0; i < segments.size(); i++) {
    if (!segments[i].active) {
      loadBalancer->MarkSegmentCompleted(i);
    }
  }
  
  return loadBalancer->Rebalance();
}

