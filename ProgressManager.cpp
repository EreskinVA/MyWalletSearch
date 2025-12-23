/*
 * Progress Manager Implementation
 * Реализация сохранения и восстановления прогресса
 */

#include "ProgressManager.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <ctime>
#include <sys/stat.h>

#define PROGRESS_FILE_VERSION 1

ProgressManager::ProgressManager() {
  progressFile = "vanitysearch_progress.dat";
  autoSaveEnabled = false;
  autoSaveInterval = 300;  // 5 минут по умолчанию
  lastAutoSave = time(NULL);
}

ProgressManager::~ProgressManager() {
}

void ProgressManager::SetProgressFile(const std::string &filename) {
  progressFile = filename;
}

bool ProgressManager::ProgressFileExists() const {
  struct stat buffer;
  return (stat(progressFile.c_str(), &buffer) == 0);
}

SearchProgress ProgressManager::CreateProgress(int bitRange, const std::string &targetAddr) {
  SearchProgress progress;
  progress.bitRange = bitRange;
  progress.totalKeysChecked = 0;
  progress.startTime = time(NULL);
  progress.lastSaveTime = time(NULL);
  progress.targetAddress = targetAddr;
  progress.version = PROGRESS_FILE_VERSION;
  progress.segments.clear();
  return progress;
}

void ProgressManager::UpdateSegmentProgress(SearchProgress &progress, int segmentIndex,
                                             const Int &currentKey, uint64_t keysChecked) {
  if (segmentIndex >= 0 && segmentIndex < (int)progress.segments.size()) {
    Int tempKey;
    tempKey.Set((Int*)&currentKey);
    progress.segments[segmentIndex].currentKey = tempKey.GetBase16();
    progress.segments[segmentIndex].keysChecked = keysChecked;
    progress.segments[segmentIndex].lastUpdate = time(NULL);
    progress.totalKeysChecked += keysChecked;
    progress.lastSaveTime = time(NULL);
  }
}

bool ProgressManager::WriteProgressToFile(const SearchProgress &progress) {
  std::ofstream file(progressFile.c_str(), std::ios::binary);
  if (!file.is_open()) {
    printf("[ProgressManager] Ошибка: не удалось открыть файл %s для записи\n", 
           progressFile.c_str());
    return false;
  }
  
  // Заголовок файла
  file << "VANITYSEARCH_PROGRESS_V" << progress.version << "\n";
  file << "BitRange=" << progress.bitRange << "\n";
  file << "TotalKeysChecked=" << progress.totalKeysChecked << "\n";
  file << "StartTime=" << progress.startTime << "\n";
  file << "LastSaveTime=" << progress.lastSaveTime << "\n";
  file << "TargetAddress=" << progress.targetAddress << "\n";
  file << "SegmentCount=" << progress.segments.size() << "\n";
  file << "---SEGMENTS---\n";
  
  // Данные сегментов
  for (size_t i = 0; i < progress.segments.size(); i++) {
    const SegmentProgress &seg = progress.segments[i];
    file << "SEGMENT_START\n";
    file << "Name=" << seg.name << "\n";
    file << "StartPercent=" << seg.startPercent << "\n";
    file << "EndPercent=" << seg.endPercent << "\n";
    file << "Direction=" << seg.direction << "\n";
    file << "CurrentKey=" << seg.currentKey << "\n";
    file << "Active=" << (seg.active ? "1" : "0") << "\n";
    file << "KeysChecked=" << seg.keysChecked << "\n";
    file << "LastUpdate=" << seg.lastUpdate << "\n";
    file << "SEGMENT_END\n";
  }
  
  file << "---END---\n";
  file.close();
  
  return true;
}

bool ProgressManager::ReadProgressFromFile(SearchProgress &progress) {
  std::ifstream file(progressFile.c_str());
  if (!file.is_open()) {
    printf("[ProgressManager] Ошибка: не удалось открыть файл %s для чтения\n", 
           progressFile.c_str());
    return false;
  }
  
  progress.segments.clear();
  
  std::string line;
  bool inSegment = false;
  SegmentProgress currentSeg;
  
  while (std::getline(file, line)) {
    if (line.empty() || line[0] == '#') continue;
    
    // Парсинг заголовка
    if (line.find("VANITYSEARCH_PROGRESS_V") == 0) {
      std::string verStr = line.substr(23);
      progress.version = atoi(verStr.c_str());
      continue;
    }
    
    // Парсинг основных параметров
    size_t eqPos = line.find('=');
    if (eqPos != std::string::npos) {
      std::string key = line.substr(0, eqPos);
      std::string value = line.substr(eqPos + 1);
      
      if (key == "BitRange") {
        progress.bitRange = atoi(value.c_str());
      } else if (key == "TotalKeysChecked") {
        progress.totalKeysChecked = strtoull(value.c_str(), NULL, 10);
      } else if (key == "StartTime") {
        progress.startTime = (time_t)strtoull(value.c_str(), NULL, 10);
      } else if (key == "LastSaveTime") {
        progress.lastSaveTime = (time_t)strtoull(value.c_str(), NULL, 10);
      } else if (key == "TargetAddress") {
        progress.targetAddress = value;
      } else if (inSegment) {
        // Парсинг данных сегмента
        if (key == "Name") {
          currentSeg.name = value;
        } else if (key == "StartPercent") {
          currentSeg.startPercent = atof(value.c_str());
        } else if (key == "EndPercent") {
          currentSeg.endPercent = atof(value.c_str());
        } else if (key == "Direction") {
          currentSeg.direction = atoi(value.c_str());
        } else if (key == "CurrentKey") {
          currentSeg.currentKey = value;
        } else if (key == "Active") {
          currentSeg.active = (value == "1");
        } else if (key == "KeysChecked") {
          currentSeg.keysChecked = strtoull(value.c_str(), NULL, 10);
        } else if (key == "LastUpdate") {
          currentSeg.lastUpdate = (time_t)strtoull(value.c_str(), NULL, 10);
        }
      }
    }
    
    // Управление секциями сегментов
    if (line == "SEGMENT_START") {
      inSegment = true;
      currentSeg = SegmentProgress();
    } else if (line == "SEGMENT_END") {
      inSegment = false;
      progress.segments.push_back(currentSeg);
    }
  }
  
  file.close();
  
  return ValidateProgress(progress);
}

bool ProgressManager::ValidateProgress(const SearchProgress &progress) {
  // Базовая валидация
  if (progress.bitRange < 1 || progress.bitRange > 256) {
    printf("[ProgressManager] Ошибка: некорректный bitRange %d\n", progress.bitRange);
    return false;
  }
  
  if (progress.segments.empty()) {
    printf("[ProgressManager] Предупреждение: нет сегментов в файле прогресса\n");
    return false;
  }
  
  return true;
}

bool ProgressManager::SaveProgress(const SearchProgress &progress) {
  printf("[ProgressManager] Сохранение прогресса в %s...\n", progressFile.c_str());
  
  if (WriteProgressToFile(progress)) {
    printf("[ProgressManager] ✓ Прогресс сохранен успешно\n");
    printf("[ProgressManager]   Всего ключей проверено: %llu\n", 
           (unsigned long long)progress.totalKeysChecked);
    printf("[ProgressManager]   Активных сегментов: ");
    int activeCount = 0;
    for (size_t i = 0; i < progress.segments.size(); i++) {
      if (progress.segments[i].active) activeCount++;
    }
    printf("%d/%d\n", activeCount, (int)progress.segments.size());
    return true;
  }
  
  return false;
}

bool ProgressManager::LoadProgress(SearchProgress &progress) {
  if (!ProgressFileExists()) {
    printf("[ProgressManager] Файл прогресса не найден: %s\n", progressFile.c_str());
    return false;
  }
  
  printf("[ProgressManager] Загрузка прогресса из %s...\n", progressFile.c_str());
  
  if (ReadProgressFromFile(progress)) {
    printf("[ProgressManager] ✓ Прогресс загружен успешно\n");
    printf("[ProgressManager]   Битовый диапазон: %d\n", progress.bitRange);
    printf("[ProgressManager]   Целевой адрес: %s\n", progress.targetAddress.c_str());
    printf("[ProgressManager]   Всего ключей проверено: %llu\n", 
           (unsigned long long)progress.totalKeysChecked);
    printf("[ProgressManager]   Сегментов загружено: %d\n", (int)progress.segments.size());
    printf("[ProgressManager]   Время работы: %s\n", 
           FormatDuration(time(NULL) - progress.startTime).c_str());
    return true;
  }
  
  return false;
}

bool ProgressManager::ClearProgress() {
  if (ProgressFileExists()) {
    if (remove(progressFile.c_str()) == 0) {
      printf("[ProgressManager] Файл прогресса удален: %s\n", progressFile.c_str());
      return true;
    } else {
      printf("[ProgressManager] Ошибка удаления файла прогресса\n");
      return false;
    }
  }
  return true;
}

std::string ProgressManager::GetProgressStats(const SearchProgress &progress) {
  std::ostringstream oss;
  
  time_t now = time(NULL);
  time_t elapsed = now - progress.startTime;
  
  oss << "\n=== Статистика прогресса ===\n";
  oss << "Битовый диапазон: " << progress.bitRange << "\n";
  oss << "Целевой адрес: " << progress.targetAddress << "\n";
  oss << "Время работы: " << FormatDuration(elapsed) << "\n";
  oss << "Всего ключей: " << progress.totalKeysChecked << "\n";
  
  if (elapsed > 0) {
    double rate = (double)progress.totalKeysChecked / elapsed;
    oss << "Средняя скорость: " << (rate / 1000000.0) << " MKey/s\n";
  }
  
  oss << "\nСегменты:\n";
  for (size_t i = 0; i < progress.segments.size(); i++) {
    const SegmentProgress &seg = progress.segments[i];
    oss << "  " << (i+1) << ". " << seg.name;
    oss << " (" << seg.startPercent << "% -> " << seg.endPercent << "%)";
    oss << " [" << (seg.active ? "Активен" : "Завершен") << "]";
    oss << " - " << seg.keysChecked << " ключей\n";
  }
  
  oss << "============================\n";
  
  return oss.str();
}

void ProgressManager::EnableAutoSave(int intervalSeconds) {
  autoSaveEnabled = true;
  autoSaveInterval = intervalSeconds;
  lastAutoSave = time(NULL);
  printf("[ProgressManager] Автосохранение включено (интервал: %d сек)\n", intervalSeconds);
}

bool ProgressManager::ShouldSave() const {
  if (!autoSaveEnabled) return false;
  
  time_t now = time(NULL);
  return (now - lastAutoSave) >= autoSaveInterval;
}

void ProgressManager::MarkSaved() {
  lastAutoSave = time(NULL);
}

std::string ProgressManager::FormatTime(time_t t) {
  char buffer[80];
  struct tm *timeinfo = localtime(&t);
  strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", timeinfo);
  return std::string(buffer);
}

std::string ProgressManager::FormatDuration(time_t seconds) {
  char buffer[100];
  
  int days = static_cast<int>(seconds / 86400);
  int hours = static_cast<int>((seconds % 86400) / 3600);
  int mins = static_cast<int>((seconds % 3600) / 60);
  int secs = static_cast<int>(seconds % 60);
  
  if (days > 0) {
    snprintf(buffer, sizeof(buffer), "%d дн %d ч %d мин", days, hours, mins);
  } else if (hours > 0) {
    snprintf(buffer, sizeof(buffer), "%d ч %d мин %d сек", hours, mins, secs);
  } else if (mins > 0) {
    snprintf(buffer, sizeof(buffer), "%d мин %d сек", mins, secs);
  } else {
    snprintf(buffer, sizeof(buffer), "%d сек", secs);
  }
  
  return std::string(buffer);
}

