/*
 * Segment Search Extension for VanitySearch
 * Реализация сегментированного поиска
 */

#include "SegmentSearch.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <mutex>

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
  if (kangarooSearch != NULL) {
    delete kangarooSearch;
    kangarooSearch = NULL;
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
        return static_cast<int>(i);
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
    Int tmp1, tmp2;
    tmp1.Set((Int*)&seg.rangeStart);
    tmp2.Set((Int*)&seg.rangeEnd);
    printf("  Начало: %s\n", tmp1.GetBase16().c_str());
    printf("  Конец:  %s\n", tmp2.GetBase16().c_str());
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
  
  return totalProgress / segments.size();
}

void SegmentSearch::EnableProgressSaving(const std::string &progressFile, int autoSaveInterval) {
  if (progressManager == NULL) {
    progressManager = new ProgressManager();
  }
  
  progressManager->SetProgressFile(progressFile);
  progressManager->EnableAutoSave(autoSaveInterval);
  progressSavingEnabled = true;
  {
    std::lock_guard<std::mutex> lk(progressMutex);
    EnsureProgressInitialized();
  }
  
  printf("[SegmentSearch] Сохранение прогресса включено: %s\n", progressFile.c_str());
}

bool SegmentSearch::SaveProgress(const std::string &targetAddress) {
  if (!progressSavingEnabled || progressManager == NULL) {
    return false;
  }

  // Prevent concurrent saves from multiple worker threads
  if (saveInProgress.exchange(true)) {
    return false;
  }

  SearchProgress snapshot;
  {
    std::lock_guard<std::mutex> lk(progressMutex);
    EnsureProgressInitialized();
    snapshot = currentProgress;
    ExportToProgress(snapshot);
    snapshot.targetAddress = targetAddress;
    snapshot.lastSaveTime = time(NULL);
  }

  bool result = progressManager->SaveProgress(snapshot);
  {
    std::lock_guard<std::mutex> lk(progressMutex);
    if (result) {
      progressManager->MarkSaved();
      keysCheckedSinceLastSave = 0;
      currentProgress.lastSaveTime = snapshot.lastSaveTime;
    }
  }

  saveInProgress.store(false);
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
    bool doSave = false;
    std::string targetAddr;
    {
      std::lock_guard<std::mutex> lk(progressMutex);
      EnsureProgressInitialized();

      SegmentProgress &sp = currentProgress.segments[segIdx];
      sp.currentKey = segments[segIdx].currentKey.GetBase16();
      sp.keysChecked += keysChecked;
      sp.lastUpdate = time(NULL);
      sp.active = segments[segIdx].active;

      currentProgress.totalKeysChecked += keysChecked;
      keysCheckedSinceLastSave += keysChecked;

      if (progressManager != NULL && progressManager->ShouldSave() && !saveInProgress.load()) {
        doSave = true;
        targetAddr = currentProgress.targetAddress;
      }
    }

    if (doSave) {
      SaveProgress(targetAddr);
    }
  }
}

bool SegmentSearch::ShouldAutoSave() {
  if (!progressSavingEnabled || progressManager == NULL) {
    return false;
  }
  
  return progressManager->ShouldSave();
}

void SegmentSearch::EnsureProgressInitialized() {
  if ((int)currentProgress.segments.size() == (int)segments.size()) return;
  currentProgress.bitRange = bitRange;
  currentProgress.segments.clear();
  currentProgress.segments.reserve(segments.size());
  for (size_t i = 0; i < segments.size(); i++) {
    SegmentProgress sp;
    sp.name = segments[i].name;
    sp.startPercent = segments[i].startPercent;
    sp.endPercent = segments[i].endPercent;
    sp.direction = (segments[i].direction == DIRECTION_UP) ? 0 : 1;
    sp.currentKey = segments[i].currentKey.GetBase16();
    sp.active = segments[i].active;
    sp.keysChecked = 0;
    sp.lastUpdate = time(NULL);
    currentProgress.segments.push_back(sp);
  }
}

void SegmentSearch::ExportToProgress(SearchProgress &dst) const {
  dst.bitRange = bitRange;
  dst.segments.clear();
  dst.segments.reserve(segments.size());
  for (size_t i = 0; i < segments.size(); i++) {
    SegmentProgress sp;
    sp.name = segments[i].name;
    sp.startPercent = segments[i].startPercent;
    sp.endPercent = segments[i].endPercent;
    sp.direction = (segments[i].direction == DIRECTION_UP) ? 0 : 1;
    sp.currentKey = segments[i].currentKey.GetBase16();
    sp.active = segments[i].active;
    if (i < currentProgress.segments.size()) sp.keysChecked = currentProgress.segments[i].keysChecked;
    else sp.keysChecked = 0;
    sp.lastUpdate = time(NULL);
    dst.segments.push_back(std::move(sp));
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
  
  loadBalancer->Initialize(static_cast<int>(segments.size()), numThreads);
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
      loadBalancer->MarkSegmentCompleted(static_cast<int>(i));
    }
  }
  
  return loadBalancer->Rebalance();
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
  
  // Запустить поиск
  bool found = kangarooSearch->Search(foundKey, 0);  // 0 = без лимита
  
  return found;
}

