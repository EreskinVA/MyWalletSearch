/*
 * Segment Search Extension for VanitySearch
 * Позволяет искать в заданных сегментах диапазона ключей
 */

#ifndef SEGMENTSEARCHH
#define SEGMENTSEARCHH

#include "Int.h"
#include "ProgressManager.h"
#include "LoadBalancer.h"
#include <vector>
#include <string>

// Направление поиска в сегменте
enum SearchDirection {
  DIRECTION_UP,    // Поиск от начала к концу (вверх)
  DIRECTION_DOWN   // Поиск от конца к началу (вниз)
};

// Структура для описания одного сегмента поиска
typedef struct {
  double startPercent;        // Начало сегмента в процентах (0.0 - 100.0)
  double endPercent;          // Конец сегмента в процентах (0.0 - 100.0)
  SearchDirection direction;  // Направление поиска
  Int rangeStart;            // Начальный ключ сегмента (вычисляется)
  Int rangeEnd;              // Конечный ключ сегмента (вычисляется)
  Int currentKey;            // Текущая позиция поиска
  bool active;               // Активен ли этот сегмент
  std::string name;          // Имя сегмента для логирования
} SearchSegment;

class SegmentSearch {

public:
  SegmentSearch();
  ~SegmentSearch();

  // Загрузить конфигурацию сегментов из файла
  bool LoadSegmentsFromFile(const std::string &filename);
  
  // Добавить сегмент вручную
  void AddSegment(double startPercent, double endPercent, 
                  SearchDirection direction, const std::string &name = "");
  
  // Инициализировать все сегменты для заданного битового диапазона
  void InitializeSegments(int bitRange);
  
  // Получить начальный ключ для потока
  bool GetStartingKey(int threadId, Int &key);
  
  // Получить следующий ключ в текущем сегменте
  bool GetNextKey(int threadId, Int &key);
  
  // Проверить, завершен ли поиск во всех сегментах
  bool IsSearchComplete();
  
  // Вывести информацию о сегментах
  void PrintSegments();
  
  // Получить количество активных сегментов
  int GetActiveSegmentCount() const { return activeSegments; }
  
  // Получить общий прогресс поиска
  double GetOverallProgress();
  
  // Управление прогрессом
  void EnableProgressSaving(const std::string &progressFile, int autoSaveInterval = 300);
  bool SaveProgress(const std::string &targetAddress);
  bool LoadProgress(const std::string &targetAddress);
  void UpdateProgress(int threadId, uint64_t keysChecked);
  bool ShouldAutoSave();
  
  // Балансировка нагрузки
  void EnableLoadBalancing(int numThreads, int rebalanceInterval = 60);
  void UpdateLoadStats(int threadId, uint64_t keysChecked, double keysPerSecond);
  bool PerformRebalance();

private:
  std::vector<SearchSegment> segments;
  int bitRange;
  Int fullRangeStart;    // 2^(n-1)
  Int fullRangeEnd;      // 2^n - 1
  Int fullRangeSize;     // Размер полного диапазона
  int activeSegments;
  
  // Progress management
  ProgressManager *progressManager;
  SearchProgress currentProgress;
  bool progressSavingEnabled;
  uint64_t keysCheckedSinceLastSave;
  
  // Load balancing
  LoadBalancer *loadBalancer;
  bool loadBalancingEnabled;
  
  // Вычислить ключ для заданного процента
  void CalculateKeyAtPercent(double percent, Int &result);
  
  // Распределить сегменты между потоками (с учётом балансировки)
  int GetSegmentForThread(int threadId);
  
  // Конвертация между SegmentProgress и SearchSegment
  void ExportToProgress();
  void ImportFromProgress();
};

#endif // SEGMENTSEARCHH

