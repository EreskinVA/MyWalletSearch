/*
 * Adaptive Priority Manager
 * Адаптивное изменение приоритетов сегментов
 */

#ifndef ADAPTIVEPRIORITYH
#define ADAPTIVEPRIORITYH

#include <vector>
#include <map>
#include <cstdint>

// Приоритет сегмента
typedef struct {
  int segmentId;
  double priority;        // 0.0 - 1.0 (выше = важнее)
  double successRate;     // Вероятность успеха
  double coverage;        // Покрытие поиска (%)
  uint64_t keysChecked;
  int rank;              // Ранг по приоритету (1 = highest)
} SegmentPriority;

class AdaptivePriorityManager {

public:
  AdaptivePriorityManager();
  ~AdaptivePriorityManager();

  // Инициализация
  void Initialize(int numSegments);
  
  // Обновить статистику сегмента
  void UpdateSegmentMetrics(int segmentId, uint64_t keysChecked, 
                            double coverage, double successRate = 0.0);
  
  // Пересчитать приоритеты
  void RecalculatePriorities();
  
  // Получить приоритет сегмента
  double GetPriority(int segmentId) const;
  
  // Получить все приоритеты (отсортированные)
  std::vector<SegmentPriority> GetPrioritiesRanked() const;
  
  // Рекомендовать следующий сегмент для потока
  int RecommendSegment(const std::vector<bool> &segmentActive) const;
  
  // Настройка весов для расчёта приоритета
  void SetWeights(double coverageWeight, double successWeight);

private:
  int numSegments;
  std::vector<SegmentPriority> priorities;
  
  double coverageWeight;    // Вес покрытия в расчёте
  double successRateWeight; // Вес успешности в расчёте
  
  // Нормализация приоритетов
  void NormalizePriorities();
  
  // Расчёт приоритета для сегмента
  double CalculatePriority(const SegmentPriority &priority) const;
};

#endif // ADAPTIVEPRIORITYH

