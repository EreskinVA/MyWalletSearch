/*
 * Pollard's Kangaroo Algorithm for ECDLP
 * Решение задачи дискретного логарифма на эллиптических кривых
 * Сложность: O(sqrt(N)) вместо O(N)
 */

#ifndef KANGAROOSEARCHH
#define KANGAROOSEARCHH

#ifdef _WIN32
#define _USE_MATH_DEFINES
#endif

#include "Int.h"
#include "Point.h"
#include "SECP256k1.h"
#include <map>
#include <vector>
#include <string>
#include <cstdint>
#include <ctime>

// Distinguished Point - точка для collision detection
typedef struct {
  Point position;          // Позиция кенгуру
  Int distance;           // Пройденное расстояние
  bool isTame;            // Ручной или дикий кенгуру
  std::string dpHash;     // Хеш distinguished point
  time_t timestamp;       // Время обнаружения
} DistinguishedPoint;

// Состояние кенгуру
typedef struct {
  Point position;         // Текущая позиция
  Int distance;          // Пройденное расстояние
  uint64_t jumps;        // Количество прыжков
  bool active;           // Активен ли
} KangarooState;

class KangarooSearch {

public:
  KangarooSearch(Secp256K1 *secp);
  ~KangarooSearch();

  // Инициализация для поиска в диапазоне
  void Initialize(const Int &rangeStart, const Int &rangeEnd, 
                  const Point &targetPublicKey);
  
  // Настройки алгоритма
  void SetJumpDistance(int avgBits);          // Средняя длина прыжка
  void SetDistinguishedBits(int bits);        // Биты для DP (обычно 16-24)
  void SetNumKangaroos(int tame, int wild);   // Количество кенгуру
  
  // Основной цикл поиска
  bool Search(Int &foundPrivateKey, int maxIterations = 0);
  
  // Шаг одного кенгуру
  bool StepKangaroo(KangarooState &kangaroo, bool isTame);
  
  // Проверка на distinguished point
  bool IsDistinguished(const Point &p);
  
  // Проверка коллизии
  bool CheckCollision(const DistinguishedPoint &dp, Int &privateKey);
  
  // Статистика
  uint64_t GetTotalJumps() const;
  uint64_t GetDistinguishedPointsFound() const;
  double GetExpectedOperations() const;
  void PrintStatistics() const;
  
  // Сохранение/загрузка состояния для long-running поиска
  bool SaveState(const std::string &filename);
  bool LoadState(const std::string &filename);

private:
  Secp256K1 *secp;
  
  // Параметры поиска
  Int rangeStart;
  Int rangeEnd;
  Int rangeSize;
  Point targetPubKey;
  
  // Настройки алгоритма
  int jumpDistanceBits;   // Средний размер прыжка (обычно sqrt(range)/2^8)
  int distinguishedBits;  // Количество нулевых бит для DP
  int numTameKangaroos;   // Количество ручных кенгуру
  int numWildKangaroos;   // Количество диких кенгуру
  
  // Состояние кенгуру
  std::vector<KangarooState> tameKangaroos;
  std::vector<KangarooState> wildKangaroos;
  
  // Distinguished points для collision detection
  std::map<std::string, DistinguishedPoint> distinguishedPoints;
  
  // Предвычисленные прыжки (для скорости)
  std::vector<Point> jumpTable;
  std::vector<Int> jumpDistances;
  
  // Статистика
  uint64_t totalJumps;
  uint64_t distinguishedPointsFound;
  time_t searchStartTime;
  
  // Вспомогательные методы
  void InitializeJumpTable();
  void InitializeKangaroos();
  
  Int CalculateJumpDistance(const Point &position);
  Point ComputeJump(const Point &position, Int &jumpDist);
  
  std::string ComputeDistinguishedHash(const Point &p);
  bool IsCollision(const DistinguishedPoint &dp1, const DistinguishedPoint &dp2);
  
  Int ReconstructPrivateKey(const DistinguishedPoint &tameDP, 
                             const DistinguishedPoint &wildDP);
};

#endif // KANGAROOSEARCHH

