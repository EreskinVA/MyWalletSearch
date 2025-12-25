/*
 * Segment Search Extension for VanitySearch
 * Реализация сегментированного поиска
 */

#include "SegmentSearch.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <cstring>
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
                                SearchDirection direction, const std::string &name, int priority) {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif
  
  SearchSegment seg;
  seg.rangeMode = RANGE_PERCENT;
  seg.startPercent = startPercent;
  seg.endPercent = endPercent;
  seg.direction = direction;
  seg.active = true;
  seg.name = name.empty() ? "Segment_" + std::to_string(segments.size() + 1) : name;
  seg.priority = (priority <= 0 ? 1 : priority);
  
  segments.push_back(seg);
  activeSegments++;
  
  std::string segName = seg.name;
  std::string dirStr = (direction == DIRECTION_UP ? "ВВЕРХ" : "ВНИЗ");
  int prio = seg.priority;
  
#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif
  
  printf("[SegmentSearch] Добавлен сегмент: %s (%.6f%% -> %.6f%%, направление: %s, priority=%d)\n",
         segName.c_str(), startPercent, endPercent, dirStr.c_str(), prio);
}

void SegmentSearch::AddSegmentRange(const Int &startKey, const Int &endKey,
                                    SearchDirection direction, const std::string &name, int priority) {
#ifndef WIN64
  pthread_mutex_lock(&mutex);
#else
  WaitForSingleObject(mutex, INFINITE);
#endif

  SearchSegment seg;
  seg.rangeMode = RANGE_ABSOLUTE;
  seg.startPercent = -1.0;
  seg.endPercent = -1.0;
  seg.direction = direction;
  seg.active = true;
  seg.name = name.empty() ? "Segment_" + std::to_string(segments.size() + 1) : name;
  seg.priority = (priority <= 0 ? 1 : priority);
  seg.rangeStart.Set(&startKey);
  seg.rangeEnd.Set(&endKey);
  // currentKey выставим в InitializeSegments (с нормализацией UP/DOWN)

  segments.push_back(seg);
  activeSegments++;

  std::string segName = seg.name;
  std::string dirStr = (direction == DIRECTION_UP ? "ВВЕРХ" : "ВНИЗ");
  int prio = seg.priority;
  std::string sHex = seg.rangeStart.GetBase16();
  std::string eHex = seg.rangeEnd.GetBase16();
  std::string sDec = seg.rangeStart.GetBase10();
  std::string eDec = seg.rangeEnd.GetBase10();

#ifndef WIN64
  pthread_mutex_unlock(&mutex);
#else
  ReleaseMutex(mutex);
#endif

  printf("[SegmentSearch] Добавлен сегмент: %s (ABS %s -> %s, hex %s -> %s, направление: %s, priority=%d)\n",
         segName.c_str(), sDec.c_str(), eDec.c_str(), sHex.c_str(), eHex.c_str(), dirStr.c_str(), prio);
}

static bool IsAllDigits(const std::string &s) {
  if (s.empty()) return false;
  size_t i = 0;
  if (s[0] == '+') i = 1;
  if (i >= s.size()) return false;
  for (; i < s.size(); i++) {
    if (s[i] < '0' || s[i] > '9') return false;
  }
  return true;
}

static bool LooksLikePercent(const std::string &a, const std::string &b) {
  auto hasDot = [](const std::string &s) { return s.find('.') != std::string::npos; };
  auto hasPct = [](const std::string &s) { return !s.empty() && s.back() == '%'; };
  if (hasDot(a) || hasDot(b) || hasPct(a) || hasPct(b)) return true;
  // Совместимость со старым форматом: "45 54 up"
  if (IsAllDigits(a) && IsAllDigits(b) && a.size() <= 3 && b.size() <= 3) {
    int ai = atoi(a.c_str());
    int bi = atoi(b.c_str());
    return (ai >= 0 && ai <= 100 && bi >= 0 && bi <= 100);
  }
  return false;
}

static bool ParseIntAuto(const std::string &tok, Int &out) {
  std::string s = tok;
  if (s.empty()) return false;
  if (s.rfind("0x", 0) == 0 || s.rfind("0X", 0) == 0) {
    std::string hex = s.substr(2);
    out.SetBase16((char *)hex.c_str());
    return true;
  }
  bool hasHexAlpha = false;
  for (char c : s) {
    if ((c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) { hasHexAlpha = true; break; }
  }
  if (hasHexAlpha) {
    out.SetBase16((char *)s.c_str());
    return true;
  }
  out.SetBase10((char *)s.c_str());
  return true;
}

static bool IsModeToken(const std::string &s, const char *tok) {
  if (s.size() != strlen(tok)) return false;
  for (size_t i = 0; i < s.size(); i++) {
    char c = (char)tolower(s[i]);
    if (c != tok[i]) return false;
  }
  return true;
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
    
    // Поддерживаем два формата:
    //
    // (A) Проценты:
    //   startPercent endPercent direction [name] [priority]
    //   45.0 54.0 up seg1 10
    //
    // (B) Абсолютные ключи (decimal/hex):
    //   startKey endKey direction [name] [priority]
    //   1711857850057426331109 1711857850057426331200 up
    //   0x5CCB... 0x5CCE... down mySeg 5
    std::istringstream iss(line);
    std::vector<std::string> toks;
    std::string t;
    while (iss >> t) toks.push_back(t);
    if (toks.size() < 3) {
      printf("[SegmentSearch] Предупреждение: неверный формат строки %d, пропускаем\n", lineNum);
      continue;
    }

    // Optional explicit mode marker to avoid ambiguity:
    //   pct 10 80 up ...
    //   abs 171185... 171185... up ...
    //   dec 171185... 171185... up ...
    // If отсутствует — используем эвристику (совместимость со старыми percent-файлами).
    bool forcedPercent = false;
    bool forcedAbsolute = false;
    size_t baseIdx = 0;
    if (IsModeToken(toks[0], "pct") || IsModeToken(toks[0], "percent")) {
      forcedPercent = true;
      baseIdx = 1;
    } else if (IsModeToken(toks[0], "abs") || IsModeToken(toks[0], "dec") || IsModeToken(toks[0], "key")) {
      forcedAbsolute = true;
      baseIdx = 1;
    }

    if (toks.size() < baseIdx + 3) {
      printf("[SegmentSearch] Предупреждение: неверный формат строки %d, пропускаем\n", lineNum);
      continue;
    }

    std::string startTok = toks[baseIdx + 0];
    std::string endTok = toks[baseIdx + 1];
    std::string dirStr = toks[baseIdx + 2];

    std::string name = "Line_" + std::to_string(lineNum);
    int priority = 1;
    if (toks.size() >= baseIdx + 4) {
      std::string last = toks.back();
      bool lastIsPrio = IsAllDigits(last) && last.size() <= 6;
      if (lastIsPrio) {
        priority = atoi(last.c_str());
      }
      size_t nameEnd = toks.size();
      if (lastIsPrio) nameEnd--;
      if (nameEnd > baseIdx + 3) {
        name.clear();
        for (size_t i = baseIdx + 3; i < nameEnd; i++) {
          if (!name.empty()) name.push_back('_');
          name += toks[i];
        }
      }
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
    
    bool isPercent = forcedPercent || (!forcedAbsolute && LooksLikePercent(startTok, endTok));
    if (isPercent) {
      if (!startTok.empty() && startTok.back() == '%') startTok.pop_back();
      if (!endTok.empty() && endTok.back() == '%') endTok.pop_back();
      double start = atof(startTok.c_str());
      double end = atof(endTok.c_str());
      if (start < 0.0 || start > 100.0 || end < 0.0 || end > 100.0) {
        printf("[SegmentSearch] Предупреждение: проценты вне диапазона 0-100 в строке %d, пропускаем\n", lineNum);
        continue;
      }
      AddSegment(start, end, dir, name, priority);
    } else {
      Int sKey, eKey;
      if (!ParseIntAuto(startTok, sKey) || !ParseIntAuto(endTok, eKey)) {
        printf("[SegmentSearch] Предупреждение: не удалось распарсить ключи в строке %d, пропускаем\n", lineNum);
        continue;
      }
      AddSegmentRange(sKey, eKey, dir, name, priority);
    }
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
  std::vector<std::string> segStartDecStrs;
  std::vector<std::string> segEndDecStrs;
  std::vector<int> segRangeModes;
  
  for (size_t i = 0; i < segments.size(); i++) {
    if (segments[i].rangeMode == RANGE_PERCENT) {
      CalculateKeyAtPercent(segments[i].startPercent, segments[i].rangeStart);
      CalculateKeyAtPercent(segments[i].endPercent, segments[i].rangeEnd);
    }

    // Кламп в общий диапазон (защита от ошибок конфигурации)
    if (segments[i].rangeStart.IsLower(&fullRangeStart)) segments[i].rangeStart.Set(&fullRangeStart);
    if (segments[i].rangeStart.IsGreater(&fullRangeEnd)) segments[i].rangeStart.Set(&fullRangeEnd);
    if (segments[i].rangeEnd.IsLower(&fullRangeStart)) segments[i].rangeEnd.Set(&fullRangeStart);
    if (segments[i].rangeEnd.IsGreater(&fullRangeEnd)) segments[i].rangeEnd.Set(&fullRangeEnd);

    // Нормализация границ в зависимости от направления
    if (segments[i].direction == DIRECTION_UP) {
      if (segments[i].rangeStart.IsGreater(&segments[i].rangeEnd)) {
        Int tmp;
        tmp.Set(&segments[i].rangeStart);
        segments[i].rangeStart.Set(&segments[i].rangeEnd);
        segments[i].rangeEnd.Set(&tmp);
      }
    } else {
      // DOWN: rangeStart должен быть верхней границей
      if (segments[i].rangeStart.IsLower(&segments[i].rangeEnd)) {
        Int tmp;
        tmp.Set(&segments[i].rangeStart);
        segments[i].rangeStart.Set(&segments[i].rangeEnd);
        segments[i].rangeEnd.Set(&tmp);
      }
    }
    
    // Установить начальную позицию в зависимости от направления
    if (segments[i].direction == DIRECTION_UP) {
      segments[i].currentKey.Set(&segments[i].rangeStart);
    } else {
      // Для DOWN ожидаемый формат в конфиге: startPercent > endPercent (пример: 10 -> 5 down)
      // Значит начинать нужно с верхней границы (rangeStart) и двигаться к нижней (rangeEnd).
      segments[i].currentKey.Set(&segments[i].rangeStart);
    }
    
    segNames.push_back(segments[i].name);
    segStartStrs.push_back(segments[i].rangeStart.GetBase16());
    segEndStrs.push_back(segments[i].rangeEnd.GetBase16());
    segStartDecStrs.push_back(segments[i].rangeStart.GetBase10());
    segEndDecStrs.push_back(segments[i].rangeEnd.GetBase10());
    segRangeModes.push_back((int)segments[i].rangeMode);
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
    if (segRangeModes[i] == (int)RANGE_ABSOLUTE) {
      printf("[SegmentSearch] %s: ABS %s -> %s (hex %s -> %s)\n",
             segNames[i].c_str(),
             segStartDecStrs[i].c_str(),
             segEndDecStrs[i].c_str(),
             segStartStrs[i].c_str(),
             segEndStrs[i].c_str());
    } else {
      printf("[SegmentSearch] %s: %s -> %s\n",
             segNames[i].c_str(),
             segStartStrs[i].c_str(),
             segEndStrs[i].c_str());
    }
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
  
  // Простое распределение с учетом приоритета: weighted round-robin.
  // weight = max(1, priority), capped to avoid huge vectors.
  std::vector<int> weighted;
  weighted.reserve(segments.size());
  for (size_t i = 0; i < segments.size(); i++) {
    if (!segments[i].active) continue;
    int w = segments[i].priority;
    if (w <= 0) w = 1;
    if (w > 1024) w = 1024;
    for (int k = 0; k < w; k++) weighted.push_back((int)i);
  }
  if (!weighted.empty()) {
    int idx = weighted[(size_t)threadId % weighted.size()];
#ifndef WIN64
    pthread_mutex_unlock(&mutex);
#else
    ReleaseMutex(mutex);
#endif
    return idx;
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
  
  // Добавляем небольшое смещение для потока, чтобы потоки не искали в одном месте.
  // Для DOWN смещение должно идти "вниз", иначе мы улетим за верхнюю границу.
  Int offset((int64_t)threadId);
  if (seg.direction == DIRECTION_UP) {
    key.Add(&offset);
  } else {
    key.Sub(&offset);
  }
  
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
    // Для DOWN идём вниз от rangeStart к rangeEnd, значит завершение когда currentKey < rangeEnd
    if (seg.currentKey.IsLower(&seg.rangeEnd)) {
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
  std::vector<std::string> startDecStrs;
  std::vector<std::string> endDecStrs;
  std::vector<int> rangeModes;
  std::vector<int> priorities;
  
  for (size_t i = 0; i < segments.size(); i++) {
    const SearchSegment &seg = segments[i];
    segNames.push_back(seg.name);
    startPercents.push_back(seg.startPercent);
    endPercents.push_back(seg.endPercent);
    directions.push_back(seg.direction == DIRECTION_UP ? "ВВЕРХ ↑" : "ВНИЗ ↓");
    actives.push_back(seg.active);
    rangeModes.push_back((int)seg.rangeMode);
    priorities.push_back(seg.priority);
    Int tmp1, tmp2;
    tmp1.Set((Int*)&seg.rangeStart);
    tmp2.Set((Int*)&seg.rangeEnd);
    startStrs.push_back(tmp1.GetBase16());
    endStrs.push_back(tmp2.GetBase16());
    startDecStrs.push_back(tmp1.GetBase10());
    endDecStrs.push_back(tmp2.GetBase10());
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
    if (rangeModes[i] == (int)RANGE_ABSOLUTE) {
      printf("  Диапазон: ABS\n");
    } else {
      printf("  Диапазон: %.2f%% -> %.2f%%\n", startPercents[i], endPercents[i]);
    }
    printf("  Направление: %s\n", directions[i].c_str());
    printf("  Статус: %s\n", actives[i] ? "Активен" : "Завершен");
    printf("  Priority: %d\n", priorities[i]);
    if (rangeModes[i] == (int)RANGE_ABSOLUTE) {
      printf("  Начало: %s (hex %s)\n", startDecStrs[i].c_str(), startStrs[i].c_str());
      printf("  Конец:  %s (hex %s)\n", endDecStrs[i].c_str(), endStrs[i].c_str());
    } else {
      printf("  Начало: %s\n", startStrs[i].c_str());
      printf("  Конец:  %s\n", endStrs[i].c_str());
    }
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
    // Обновляем текущую позицию сегмента, чтобы прогресс/движение UP/DOWN было корректным.
    // В VanitySearch счётчик keysChecked обычно учитывает 6 вариантов (point + endo1 + endo2 + sym + ...),
    // поэтому один "шаг" по скаляру ≈ keysChecked/6.
    uint64_t scalarStep = keysChecked / 6ULL;
    if (scalarStep > 0) {
      if (segments[segIdx].direction == DIRECTION_UP) {
        segments[segIdx].currentKey.Add(scalarStep);
        if (segments[segIdx].currentKey.IsGreater(&segments[segIdx].rangeEnd)) {
          segments[segIdx].active = false;
          activeSegments--;
          printf("[SegmentSearch] Сегмент %s завершен (поиск вверх)\n", segments[segIdx].name.c_str());
        }
      } else {
        segments[segIdx].currentKey.Sub(scalarStep);
        if (segments[segIdx].currentKey.IsLower(&segments[segIdx].rangeEnd)) {
          segments[segIdx].active = false;
          activeSegments--;
          printf("[SegmentSearch] Сегмент %s завершен (поиск вниз)\n", segments[segIdx].name.c_str());
        }
      }
    }

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
  // NOTE: caller must hold `mutex`
  
  currentProgress.bitRange = bitRange;
  // НЕ очищаем segments - сохраняем существующие значения keysChecked
  // Обновляем только изменяемые поля
  for (size_t i = 0; i < segments.size(); i++) {
    if (i < currentProgress.segments.size()) {
      // Обновляем существующий сегмент
      currentProgress.segments[i].currentKey = segments[i].currentKey.GetBase16();
      currentProgress.segments[i].active = segments[i].active;
      currentProgress.segments[i].lastUpdate = time(NULL);
      currentProgress.segments[i].rangeMode = (int)segments[i].rangeMode;
      currentProgress.segments[i].rangeStart = segments[i].rangeStart.GetBase16();
      currentProgress.segments[i].rangeEnd = segments[i].rangeEnd.GetBase16();
      currentProgress.segments[i].priority = segments[i].priority;
      // keysChecked сохраняем из текущего прогресса (не сбрасываем!)
    } else {
      // Создаем новый сегмент
      SegmentProgress sp;
      sp.name = segments[i].name;
      sp.startPercent = segments[i].startPercent;
      sp.endPercent = segments[i].endPercent;
      sp.direction = (segments[i].direction == DIRECTION_UP) ? 0 : 1;
      sp.rangeMode = (int)segments[i].rangeMode;
      sp.rangeStart = segments[i].rangeStart.GetBase16();
      sp.rangeEnd = segments[i].rangeEnd.GetBase16();
      sp.priority = segments[i].priority;
      sp.currentKey = segments[i].currentKey.GetBase16();
      sp.active = segments[i].active;
      sp.keysChecked = 0;  // Только для новых сегментов
      sp.lastUpdate = time(NULL);
      currentProgress.segments.push_back(sp);
    }
  }
}

void SegmentSearch::ImportFromProgress() {
  // NOTE: caller must hold `mutex`
  
  if (currentProgress.segments.size() != segments.size()) {
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

