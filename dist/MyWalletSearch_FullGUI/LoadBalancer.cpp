/*
 * Load Balancer Implementation
 * Реализация динамической балансировки
 */

#include "LoadBalancer.h"
#include <iostream>
#include <algorithm>
#include <cmath>

LoadBalancer::LoadBalancer() {
  numSegments = 0;
  numThreads = 0;
  lastRebalance = time(NULL);
  rebalanceInterval = 60;  // Ребалансировка каждую минуту
  efficiencyThreshold = 0.3;  // 30% разница для ребалансировки
  adaptiveBalancing = true;
}

LoadBalancer::~LoadBalancer() {
  segmentStats.clear();
  threadAssignments.clear();
  segmentCompleted.clear();
}

void LoadBalancer::Initialize(int numSegs, int numThreads) {
  this->numSegments = numSegs;
  this->numThreads = numThreads;
  
  segmentStats.clear();
  segmentCompleted.clear();
  threadAssignments.clear();
  
  // Инициализация статистики сегментов
  for (int i = 0; i < numSegments; i++) {
    SegmentStats stats;
    stats.segmentId = i;
    stats.keysChecked = 0;
    stats.keysPerSecond = 0.0;
    stats.activeThreads = 0;
    stats.lastUpdate = time(NULL);
    stats.efficiency = 1.0;
    
    segmentStats.push_back(stats);
    segmentCompleted.push_back(false);
  }
  
  // Начальное распределение потоков (round-robin)
  for (int t = 0; t < numThreads; t++) {
    int segId = t % numSegments;
    
    ThreadAssignment assignment;
    assignment.threadId = t;
    assignment.segmentId = segId;
    assignment.assignedAt = time(NULL);
    assignment.keysChecked = 0;
    
    threadAssignments[t] = assignment;
    segmentStats[segId].activeThreads++;
  }
  
  printf("[LoadBalancer] Инициализирован: %d сегментов, %d потоков\n", 
         numSegments, numThreads);
  printf("[LoadBalancer] Интервал ребалансировки: %d сек\n", rebalanceInterval);
}

int LoadBalancer::GetSegmentForThread(int threadId) {
  if (threadAssignments.find(threadId) != threadAssignments.end()) {
    return threadAssignments[threadId].segmentId;
  }
  
  // Если поток не назначен, назначаем на первый доступный сегмент
  for (int i = 0; i < numSegments; i++) {
    if (!segmentCompleted[i]) {
      ThreadAssignment assignment;
      assignment.threadId = threadId;
      assignment.segmentId = i;
      assignment.assignedAt = time(NULL);
      assignment.keysChecked = 0;
      
      threadAssignments[threadId] = assignment;
      segmentStats[i].activeThreads++;
      return i;
    }
  }
  
  return 0;  // Fallback
}

void LoadBalancer::UpdateSegmentStats(int segmentId, uint64_t keysChecked, double keysPerSecond) {
  if (segmentId < 0 || segmentId >= numSegments) return;
  
  segmentStats[segmentId].keysChecked += keysChecked;
  segmentStats[segmentId].keysPerSecond = keysPerSecond;
  segmentStats[segmentId].lastUpdate = time(NULL);
}

void LoadBalancer::MarkSegmentCompleted(int segmentId) {
  if (segmentId >= 0 && segmentId < numSegments) {
    segmentCompleted[segmentId] = true;
    printf("[LoadBalancer] Сегмент %d завершён\n", segmentId);
    
    // Переназначить потоки с завершённого сегмента
    for (auto &pair : threadAssignments) {
      if (pair.second.segmentId == segmentId) {
        // Найти следующий активный сегмент
        for (int i = 0; i < numSegments; i++) {
          if (!segmentCompleted[i]) {
            printf("[LoadBalancer] Поток %d переназначен: %d -> %d\n",
                   pair.first, segmentId, i);
            ReassignThread(pair.first, segmentId, i);
            break;
          }
        }
      }
    }
  }
}

bool LoadBalancer::ShouldRebalance() const {
  if (!adaptiveBalancing) return false;
  
  time_t now = time(NULL);
  return (now - lastRebalance) >= rebalanceInterval;
}

void LoadBalancer::CalculateEfficiency() {
  // Найти максимальную скорость
  double maxRate = 0.0;
  for (int i = 0; i < numSegments; i++) {
    if (!segmentCompleted[i] && segmentStats[i].keysPerSecond > maxRate) {
      maxRate = segmentStats[i].keysPerSecond;
    }
  }
  
  if (maxRate > 0) {
    for (int i = 0; i < numSegments; i++) {
      if (!segmentCompleted[i]) {
        segmentStats[i].efficiency = segmentStats[i].keysPerSecond / maxRate;
      } else {
        segmentStats[i].efficiency = 0.0;
      }
    }
  }
}

int LoadBalancer::FindSlowestSegment() const {
  int slowest = -1;
  double minRate = 1e99;
  
  for (int i = 0; i < numSegments; i++) {
    if (!segmentCompleted[i] && segmentStats[i].activeThreads > 0) {
      double effectiveRate = segmentStats[i].keysPerSecond / 
                             std::max(1, segmentStats[i].activeThreads);
      if (effectiveRate < minRate) {
        minRate = effectiveRate;
        slowest = i;
      }
    }
  }
  
  return slowest;
}

int LoadBalancer::FindFastestSegment() const {
  int fastest = -1;
  double maxRate = 0.0;
  
  for (int i = 0; i < numSegments; i++) {
    if (!segmentCompleted[i]) {
      double effectiveRate = segmentStats[i].keysPerSecond / 
                             std::max(1, segmentStats[i].activeThreads);
      if (effectiveRate > maxRate) {
        maxRate = effectiveRate;
        fastest = i;
      }
    }
  }
  
  return fastest;
}

int LoadBalancer::GetThreadCountForSegment(int segmentId) const {
  int count = 0;
  for (const auto &pair : threadAssignments) {
    if (pair.second.segmentId == segmentId) {
      count++;
    }
  }
  return count;
}

void LoadBalancer::ReassignThread(int threadId, int fromSegment, int toSegment) {
  if (threadAssignments.find(threadId) == threadAssignments.end()) return;
  
  // Обновить счётчики
  if (fromSegment >= 0 && fromSegment < numSegments) {
    segmentStats[fromSegment].activeThreads--;
  }
  if (toSegment >= 0 && toSegment < numSegments) {
    segmentStats[toSegment].activeThreads++;
  }
  
  // Переназначить поток
  threadAssignments[threadId].segmentId = toSegment;
  threadAssignments[threadId].assignedAt = time(NULL);
  threadAssignments[threadId].keysChecked = 0;
}

bool LoadBalancer::Rebalance() {
  if (!ShouldRebalance()) return false;
  
  printf("[LoadBalancer] Выполняется ребалансировка...\n");
  
  CalculateEfficiency();
  
  int slowest = FindSlowestSegment();
  int fastest = FindFastestSegment();
  
  if (slowest == -1 || fastest == -1 || slowest == fastest) {
    lastRebalance = time(NULL);
    return false;
  }
  
  // Проверить разницу в эффективности
  double effDiff = segmentStats[fastest].efficiency - segmentStats[slowest].efficiency;
  
  if (effDiff > efficiencyThreshold) {
    // Найти поток на медленном сегменте для перемещения
    int threadToMove = -1;
    int maxThreadsOnSlowest = 0;
    
    for (const auto &pair : threadAssignments) {
      if (pair.second.segmentId == slowest) {
        threadToMove = pair.first;
        maxThreadsOnSlowest++;
      }
    }
    
    // Переместить поток, если на медленном сегменте больше одного потока
    if (threadToMove != -1 && maxThreadsOnSlowest > 1) {
      printf("[LoadBalancer] Ребалансировка: поток %d перемещён с сегмента %d на сегмент %d\n",
             threadToMove, slowest, fastest);
      printf("[LoadBalancer]   Эффективность: %.2f%% -> %.2f%% (разница: %.2f%%)\n",
             segmentStats[slowest].efficiency * 100.0,
             segmentStats[fastest].efficiency * 100.0,
             effDiff * 100.0);
      
      ReassignThread(threadToMove, slowest, fastest);
      lastRebalance = time(NULL);
      return true;
    }
  }
  
  lastRebalance = time(NULL);
  return false;
}

std::vector<SegmentStats> LoadBalancer::GetAllStats() const {
  return segmentStats;
}

void LoadBalancer::PrintStats() const {
  printf("\n=== Статистика балансировки нагрузки ===\n");
  printf("Сегментов: %d | Потоков: %d\n", numSegments, numThreads);
  printf("\n");
  
  for (int i = 0; i < numSegments; i++) {
    const SegmentStats &stats = segmentStats[i];
    printf("Сегмент %d: ", i);
    
    if (segmentCompleted[i]) {
      printf("[ЗАВЕРШЁН]");
    } else {
      printf("[АКТИВЕН]");
    }
    
    printf("\n");
    printf("  Потоков: %d | ", stats.activeThreads);
    printf("Ключей: %llu | ", (unsigned long long)stats.keysChecked);
    printf("Скорость: %.2f MKey/s | ", stats.keysPerSecond / 1000000.0);
    printf("Эффективность: %.1f%%\n", stats.efficiency * 100.0);
  }
  
  printf("========================================\n\n");
}

void LoadBalancer::SetRebalanceInterval(int seconds) {
  rebalanceInterval = seconds;
  printf("[LoadBalancer] Интервал ребалансировки: %d сек\n", rebalanceInterval);
}

void LoadBalancer::SetEfficiencyThreshold(double threshold) {
  efficiencyThreshold = threshold;
  printf("[LoadBalancer] Порог эффективности: %.1f%%\n", threshold * 100.0);
}

void LoadBalancer::EnableAdaptiveBalancing(bool enable) {
  adaptiveBalancing = enable;
  printf("[LoadBalancer] Адаптивная балансировка: %s\n", enable ? "ВКЛ" : "ВЫКЛ");
}

