/*
 * Load Balancer for Dynamic Segment Distribution
 * Динамическая балансировка нагрузки между сегментами
 */

#ifndef LOADBALANCERH
#define LOADBALANCERH

#include <vector>
#include <map>
#include <ctime>

// Статистика производительности сегмента
typedef struct {
  int segmentId;
  uint64_t keysChecked;
  double keysPerSecond;
  int activeThreads;
  time_t lastUpdate;
  double efficiency;  // Относительная эффективность (0.0 - 1.0)
} SegmentStats;

// Назначение потока на сегмент
typedef struct {
  int threadId;
  int segmentId;
  time_t assignedAt;
  uint64_t keysChecked;
} ThreadAssignment;

class LoadBalancer {

public:
  LoadBalancer();
  ~LoadBalancer();

  // Инициализация для N сегментов
  void Initialize(int numSegments, int numThreads);
  
  // Получить назначение сегмента для потока
  int GetSegmentForThread(int threadId);
  
  // Обновить статистику сегмента
  void UpdateSegmentStats(int segmentId, uint64_t keysChecked, double keysPerSecond);
  
  // Пометить сегмент как завершённый
  void MarkSegmentCompleted(int segmentId);
  
  // Выполнить ребалансировку (вызывать периодически)
  bool Rebalance();
  
  // Проверить, нужна ли ребалансировка
  bool ShouldRebalance() const;
  
  // Получить статистику
  std::vector<SegmentStats> GetAllStats() const;
  void PrintStats() const;
  
  // Настройки балансировки
  void SetRebalanceInterval(int seconds);
  void SetEfficiencyThreshold(double threshold);
  void EnableAdaptiveBalancing(bool enable);

private:
  int numSegments;
  int numThreads;
  std::vector<SegmentStats> segmentStats;
  std::map<int, ThreadAssignment> threadAssignments;
  std::vector<bool> segmentCompleted;
  
  time_t lastRebalance;
  int rebalanceInterval;  // Секунды между ребалансировками
  double efficiencyThreshold;  // Порог для перераспределения
  bool adaptiveBalancing;
  
  // Вычислить эффективность сегментов
  void CalculateEfficiency();
  
  // Найти самый медленный и самый быстрый сегменты
  int FindSlowestSegment() const;
  int FindFastestSegment() const;
  
  // Переназначить поток с медленного на быстрый сегмент
  void ReassignThread(int threadId, int fromSegment, int toSegment);
  
  // Получить количество потоков на сегменте
  int GetThreadCountForSegment(int segmentId) const;
};

#endif // LOADBALANCERH

