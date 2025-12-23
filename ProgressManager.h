/*
 * Progress Manager for VanitySearch Segment Search
 * Сохранение и восстановление прогресса поиска
 */

#ifndef PROGRESSMANAGERH
#define PROGRESSMANAGERH

#include "Int.h"
#include <string>
#include <vector>
#include <ctime>

// Структура для сохранения прогресса одного сегмента
typedef struct {
  std::string name;
  double startPercent;
  double endPercent;
  int direction;  // 0 = up, 1 = down
  std::string currentKey;  // Hex representation
  bool active;
  uint64_t keysChecked;
  time_t lastUpdate;
} SegmentProgress;

// Общий прогресс поиска
typedef struct {
  int bitRange;
  uint64_t totalKeysChecked;
  time_t startTime;
  time_t lastSaveTime;
  std::vector<SegmentProgress> segments;
  std::string targetAddress;
  int version;  // Версия формата файла
} SearchProgress;

class ProgressManager {

public:
  ProgressManager();
  ~ProgressManager();

  // Инициализация с именем файла прогресса
  void SetProgressFile(const std::string &filename);
  
  // Сохранить текущий прогресс
  bool SaveProgress(const SearchProgress &progress);
  
  // Загрузить прогресс из файла
  bool LoadProgress(SearchProgress &progress);
  
  // Проверить существование файла прогресса
  bool ProgressFileExists() const;
  
  // Удалить файл прогресса (при завершении поиска)
  bool ClearProgress();
  
  // Создать структуру прогресса из текущих сегментов
  static SearchProgress CreateProgress(int bitRange, const std::string &targetAddr);
  
  // Обновить прогресс сегмента
  static void UpdateSegmentProgress(SearchProgress &progress, int segmentIndex,
                                     const Int &currentKey, uint64_t keysChecked);
  
  // Получить статистику прогресса
  std::string GetProgressStats(const SearchProgress &progress);
  
  // Автосохранение (вызывать периодически)
  void EnableAutoSave(int intervalSeconds);
  bool ShouldSave() const;
  void MarkSaved();

private:
  std::string progressFile;
  bool autoSaveEnabled;
  int autoSaveInterval;
  time_t lastAutoSave;
  
  // Сериализация/десериализация
  bool WriteProgressToFile(const SearchProgress &progress);
  bool ReadProgressFromFile(SearchProgress &progress);
  
  // Валидация прогресса
  bool ValidateProgress(const SearchProgress &progress);
  
  // Форматирование времени
  std::string FormatTime(time_t t);
  std::string FormatDuration(time_t seconds);
};

#endif // PROGRESSMANAGERH

