/*
 * Adaptive Priority Manager Implementation
 */

#include "AdaptivePriority.h"
#include <algorithm>
#include <cmath>
#include <iostream>

AdaptivePriorityManager::AdaptivePriorityManager() {
  numSegments = 0;
  coverageWeight = 0.7;      // 70% вес на покрытие
  successRateWeight = 0.3;   // 30% вес на успешность
}

AdaptivePriorityManager::~AdaptivePriorityManager() {
  priorities.clear();
}

void AdaptivePriorityManager::Initialize(int numSegs) {
  numSegments = numSegs;
  priorities.clear();
  
  for (int i = 0; i < numSegments; i++) {
    SegmentPriority sp;
    sp.segmentId = i;
    sp.priority = 1.0;  // Начальный приоритет равный
    sp.successRate = 0.5;  // Нейтральная оценка
    sp.coverage = 0.0;
    sp.keysChecked = 0;
    sp.rank = i + 1;
    
    priorities.push_back(sp);
  }
  
  printf("[AdaptivePriority] Инициализирован для %d сегментов\n", numSegments);
}

void AdaptivePriorityManager::UpdateSegmentMetrics(int segmentId, uint64_t keysChecked,
                                                     double coverage, double successRate) {
  if (segmentId < 0 || segmentId >= numSegments) return;
  
  priorities[segmentId].keysChecked = keysChecked;
  priorities[segmentId].coverage = coverage;
  
  // Обновить success rate если предоставлен
  if (successRate >= 0.0) {
    priorities[segmentId].successRate = successRate;
  }
  
  // Пересчитать приоритет
  priorities[segmentId].priority = CalculatePriority(priorities[segmentId]);
}

double AdaptivePriorityManager::CalculatePriority(const SegmentPriority &sp) const {
  // Приоритет выше для:
  // 1. Меньшего покрытия (непроверенные области)
  // 2. Высокой вероятности успеха
  
  double coverageScore = 1.0 - (sp.coverage / 100.0);  // Чем меньше покрытие, тем выше score
  double successScore = sp.successRate;
  
  double priority = (coverageWeight * coverageScore) + 
                    (successRateWeight * successScore);
  
  return std::max(0.0, std::min(1.0, priority));
}

void AdaptivePriorityManager::RecalculatePriorities() {
  // Пересчитать приоритеты для всех сегментов
  for (int i = 0; i < numSegments; i++) {
    priorities[i].priority = CalculatePriority(priorities[i]);
  }
  
  // Нормализовать
  NormalizePriorities();
  
  // Обновить ранги
  std::vector<SegmentPriority> sorted = priorities;
  std::sort(sorted.begin(), sorted.end(), 
            [](const SegmentPriority &a, const SegmentPriority &b) {
              return a.priority > b.priority;
            });
  
  for (size_t i = 0; i < sorted.size(); i++) {
    int segId = sorted[i].segmentId;
    priorities[segId].rank = static_cast<int>(i + 1);
  }
}

void AdaptivePriorityManager::NormalizePriorities() {
  double sum = 0.0;
  for (const auto &sp : priorities) {
    sum += sp.priority;
  }
  
  if (sum > 0) {
    for (auto &sp : priorities) {
      sp.priority /= sum;
    }
  }
}

double AdaptivePriorityManager::GetPriority(int segmentId) const {
  if (segmentId >= 0 && segmentId < numSegments) {
    return priorities[segmentId].priority;
  }
  return 0.0;
}

std::vector<SegmentPriority> AdaptivePriorityManager::GetPrioritiesRanked() const {
  std::vector<SegmentPriority> sorted = priorities;
  std::sort(sorted.begin(), sorted.end(),
            [](const SegmentPriority &a, const SegmentPriority &b) {
              return a.priority > b.priority;
            });
  return sorted;
}

int AdaptivePriorityManager::RecommendSegment(const std::vector<bool> &segmentActive) const {
  int bestSegment = -1;
  double bestPriority = -1.0;
  
  for (int i = 0; i < numSegments; i++) {
    if (i < (int)segmentActive.size() && segmentActive[i]) {
      if (priorities[i].priority > bestPriority) {
        bestPriority = priorities[i].priority;
        bestSegment = i;
      }
    }
  }
  
  return bestSegment;
}

void AdaptivePriorityManager::SetWeights(double coverageW, double successW) {
  // Нормализовать веса
  double total = coverageW + successW;
  if (total > 0) {
    coverageWeight = coverageW / total;
    successRateWeight = successW / total;
  }
  
  printf("[AdaptivePriority] Веса обновлены: покрытие=%.2f, успех=%.2f\n",
         coverageWeight, successRateWeight);
  
  // Пересчитать приоритеты с новыми весами
  RecalculatePriorities();
}

