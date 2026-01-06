/*
 * Pollard's Kangaroo Algorithm Implementation
 * Based on "Monte Carlo Methods for Index Computation (mod p)" by J.M. Pollard
 */

#include "KangarooSearch.h"
#include "hash/sha256.h"
#include <cmath>
#include <ctime>
#include <fstream>
#include <iostream>

#ifndef M_PI
// MSVC does not guarantee M_PI in <cmath> unless _USE_MATH_DEFINES is set.
// Define it explicitly for portability.
#define M_PI 3.14159265358979323846264338327950288
#endif

KangarooSearch::KangarooSearch(Secp256K1 *secp) {
  this->secp = secp;
  jumpDistanceBits = 16;      // По умолчанию
  distinguishedBits = 20;     // ~1 из 1M точек будет DP
  numTameKangaroos = 4;
  numWildKangaroos = 4;
  totalJumps = 0;
  distinguishedPointsFound = 0;
  searchStartTime = 0;
}

KangarooSearch::~KangarooSearch() {
  distinguishedPoints.clear();
  jumpTable.clear();
  jumpDistances.clear();
  tameKangaroos.clear();
  wildKangaroos.clear();
}

void KangarooSearch::Initialize(const Int &start, const Int &end, const Point &target) {
  rangeStart.Set(&start);
  rangeEnd.Set(&end);
  targetPubKey = target;
  
  // Вычислить размер диапазона
  rangeSize.Set(&rangeEnd);
  rangeSize.Sub(&rangeStart);
  
  printf("[Kangaroo] Инициализация поиска\n");
  printf("[Kangaroo] Диапазон: %s\n", rangeStart.GetBase16().c_str());
  printf("[Kangaroo]      до: %s\n", rangeEnd.GetBase16().c_str());
  printf("[Kangaroo] Размер: 2^%.2f\n", log2(rangeSize.ToDouble()));
  
  // Оптимальные параметры на основе размера диапазона
  // Jump distance ~ sqrt(rangeSize) / 256
  Int tempSize;
  tempSize.Set(&rangeSize);
  double rangeBits = log2(tempSize.ToDouble());
  jumpDistanceBits = (int)(rangeBits / 2.0) - 8;
  if (jumpDistanceBits < 8) jumpDistanceBits = 8;
  if (jumpDistanceBits > 32) jumpDistanceBits = 32;
  
  printf("[Kangaroo] Jump distance: 2^%d\n", jumpDistanceBits);
  printf("[Kangaroo] Distinguished bits: %d (1 из %d точек)\n", 
         distinguishedBits, 1 << distinguishedBits);
  printf("[Kangaroo] Кенгуру: %d tame, %d wild\n", numTameKangaroos, numWildKangaroos);
  
  // Инициализация
  InitializeJumpTable();
  InitializeKangaroos();
  
  searchStartTime = time(NULL);
  
  printf("[Kangaroo] ✓ Инициализация завершена\n\n");
}

void KangarooSearch::InitializeJumpTable() {
  // Создать таблицу прыжков для быстрого вычисления
  // Используем 256 предвычисленных точек
  
  jumpTable.clear();
  jumpDistances.clear();
  
  printf("[Kangaroo] Генерация таблицы прыжков...\n");
  
  for (int i = 0; i < 256; i++) {
    // Расстояние прыжка зависит от хеша позиции
    Int jumpDist;
    jumpDist.SetInt32(1);
    jumpDist.ShiftL(jumpDistanceBits);
    
    // Добавляем вариацию на основе индекса
    Int variation;
    variation.SetInt32(i);
    variation.ShiftL(jumpDistanceBits - 8);
    jumpDist.Add(&variation);
    
    // Вычислить соответствующую точку
    Point jumpPoint = secp->ComputePublicKey(&jumpDist);
    
    jumpTable.push_back(jumpPoint);
    jumpDistances.push_back(jumpDist);
  }
  
  printf("[Kangaroo] ✓ Таблица прыжков: 256 точек\n");
}

void KangarooSearch::InitializeKangaroos() {
  tameKangaroos.clear();
  wildKangaroos.clear();
  
  // Инициализация tame кенгуру (стартуют от rangeStart)
  for (int i = 0; i < numTameKangaroos; i++) {
    KangarooState kangaroo;
    
    // Начальная позиция: rangeStart + небольшое смещение
    Int startKey;
    startKey.Set(&rangeStart);
    Int offset;
    offset.SetInt32(i);
    offset.ShiftL(32);
    startKey.Add(&offset);
    
    kangaroo.position = secp->ComputePublicKey(&startKey);
    kangaroo.distance.Set(&offset);
    kangaroo.jumps = 0;
    kangaroo.active = true;
    
    tameKangaroos.push_back(kangaroo);
  }
  
  // Инициализация wild кенгуру (стартуют от targetPubKey)
  for (int i = 0; i < numWildKangaroos; i++) {
    KangarooState kangaroo;
    
    kangaroo.position = targetPubKey;  // Начинаем с целевой точки
    kangaroo.distance.SetInt32(0);     // Расстояние неизвестно
    kangaroo.jumps = 0;
    kangaroo.active = true;
    
    wildKangaroos.push_back(kangaroo);
  }
  
  printf("[Kangaroo] ✓ Кенгуру инициализированы\n");
}

Int KangarooSearch::CalculateJumpDistance(const Point &position) {
  // Выбор прыжка на основе хеша позиции
  // Детерминированно, но pseudo-random
  
  unsigned char hash[32];
  sha256(reinterpret_cast<const uint8_t*>(position.x.bits64), 32, hash);
  
  // Используем первый байт для индекса
  int index = hash[0];
  
  return jumpDistances[index];
}

Point KangarooSearch::ComputeJump(const Point &position, Int &jumpDist) {
  // Вычислить следующую позицию после прыжка
  
  unsigned char hash[32];
  Int tempX;
  tempX.Set(&position.x);
  sha256(reinterpret_cast<const uint8_t*>(tempX.bits64), 32, hash);
  
  int index = hash[0];
  jumpDist.Set(&jumpDistances[index]);
  
  // position + jumpTable[index]
  Point tempPos = position;
  return secp->AddDirect(tempPos, jumpTable[index]);
}

bool KangarooSearch::IsDistinguished(const Point &p) {
  // Точка distinguished если последние N бит её хеша = 0
  
  unsigned char hash[32];
  Int tempX;
  tempX.Set(&p.x);
  sha256(reinterpret_cast<const uint8_t*>(tempX.bits64), 32, hash);
  
  // Проверяем последние биты
  uint32_t check = *(uint32_t*)hash;
  uint32_t mask = (1 << distinguishedBits) - 1;
  
  return (check & mask) == 0;
}

std::string KangarooSearch::ComputeDistinguishedHash(const Point &p) {
  // Уникальный хеш для distinguished point
  unsigned char hash[32];
  Int tempX;
  tempX.Set(&p.x);
  sha256(reinterpret_cast<const uint8_t*>(tempX.bits64), 32, hash);
  
  char hex[65];
  for (int i = 0; i < 32; i++) {
    // macOS/clang: sprintf помечен deprecated. Нам нужно строго 2 символа + '\0'.
    // Пишем в окно длиной 3 байта (2 hex + terminator).
    snprintf(hex + i * 2, 3, "%02x", hash[i]);
  }
  
  return std::string(hex);
}

bool KangarooSearch::StepKangaroo(KangarooState &kangaroo, bool isTame) {
  if (!kangaroo.active) return false;
  
  // Сделать один прыжок
  Int jumpDist;
  Point newPosition = ComputeJump(kangaroo.position, jumpDist);
  
  kangaroo.position = newPosition;
  kangaroo.distance.Add(&jumpDist);
  kangaroo.jumps++;
  totalJumps++;
  
  // Проверка на distinguished point
  if (IsDistinguished(kangaroo.position)) {
    DistinguishedPoint dp;
    dp.position = kangaroo.position;
    dp.distance.Set(&kangaroo.distance);
    dp.isTame = isTame;
    dp.dpHash = ComputeDistinguishedHash(kangaroo.position);
    dp.timestamp = time(NULL);
    
    // Сохранить DP
    distinguishedPoints[dp.dpHash] = dp;
    distinguishedPointsFound++;
    
    return true;  // Found DP
  }
  
  return false;
}

bool KangarooSearch::CheckCollision(const DistinguishedPoint &dp, Int &privateKey) {
  // Проверить, есть ли коллизия с DP другого типа
  
  auto it = distinguishedPoints.find(dp.dpHash);
  if (it == distinguishedPoints.end()) {
    return false;
  }
  
  const DistinguishedPoint &storedDP = it->second;
  
  // Коллизия только если разные типы кенгуру
  if (storedDP.isTame == dp.isTame) {
    return false;
  }
  
  // COLLISION! Восстанавливаем приватный ключ
  printf("\n[Kangaroo] 🎉 COLLISION DETECTED!\n");
  Int tempDist1, tempDist2;
  tempDist1.Set((Int*)(storedDP.isTame ? &storedDP.distance : &dp.distance));
  tempDist2.Set((Int*)(!storedDP.isTame ? &storedDP.distance : &dp.distance));
  printf("[Kangaroo] Tame distance: %s\n", tempDist1.GetBase16().c_str());
  printf("[Kangaroo] Wild distance: %s\n", tempDist2.GetBase16().c_str());
  
  privateKey = ReconstructPrivateKey(
    storedDP.isTame ? storedDP : dp,
    storedDP.isTame ? dp : storedDP
  );
  
  return true;
}

Int KangarooSearch::ReconstructPrivateKey(const DistinguishedPoint &tameDP,
                                           const DistinguishedPoint &wildDP) {
  // Математика Pollard's Kangaroo:
  // Tame: P_tame = (rangeStart + d_tame) * G
  // Wild: P_wild = TargetPubKey - d_wild * G = k * G - d_wild * G
  //
  // При коллизии: P_tame = P_wild
  // (rangeStart + d_tame) * G = (k - d_wild) * G
  // rangeStart + d_tame = k - d_wild
  // k = rangeStart + d_tame + d_wild
  
  Int privateKey;
  Int tempTame, tempWild;
  tempTame.Set((Int*)&tameDP.distance);
  tempWild.Set((Int*)&wildDP.distance);
  
  privateKey.Set(&rangeStart);
  privateKey.Add(&tempTame);
  privateKey.Add(&tempWild);
  
  // Модуль по order кривой для корректности
  privateKey.Mod(&secp->order);
  
  return privateKey;
}

bool KangarooSearch::Search(Int &foundPrivateKey, int maxIterations) {
  printf("[Kangaroo] 🦘 Начинаем поиск...\n\n");
  
  uint64_t iteration = 0;
  time_t lastStatus = time(NULL);
  
  while (true) {
    // Проверка лимита итераций
    if (maxIterations > 0 && iteration >= (uint64_t)maxIterations) {
      printf("[Kangaroo] Достигнут лимит итераций: %d\n", maxIterations);
      return false;
    }
    
    // Шаг для всех tame кенгуру
    for (auto &kangaroo : tameKangaroos) {
      if (StepKangaroo(kangaroo, true)) {
        // Found distinguished point - проверяем collision
        DistinguishedPoint dp;
        dp.position = kangaroo.position;
        dp.distance.Set(&kangaroo.distance);
        dp.isTame = true;
        dp.dpHash = ComputeDistinguishedHash(kangaroo.position);
        
        if (CheckCollision(dp, foundPrivateKey)) {
          PrintStatistics();
          return true;
        }
      }
    }
    
    // Шаг для всех wild кенгуру
    for (auto &kangaroo : wildKangaroos) {
      if (StepKangaroo(kangaroo, false)) {
        DistinguishedPoint dp;
        dp.position = kangaroo.position;
        dp.distance.Set(&kangaroo.distance);
        dp.isTame = false;
        dp.dpHash = ComputeDistinguishedHash(kangaroo.position);
        
        if (CheckCollision(dp, foundPrivateKey)) {
          PrintStatistics();
          return true;
        }
      }
    }
    
    iteration++;
    
    // Статус каждые 10 секунд
    time_t now = time(NULL);
    if (now - lastStatus >= 10) {
      double mkeysPerSec = (totalJumps / 1000000.0) / (now - searchStartTime + 1);
      double progress = GetExpectedOperations();
      
      printf("\r[Kangaroo] Jumps: %llu | DPs: %llu | Speed: %.2f MKey/s | Progress: %.6f%%",
             (unsigned long long)totalJumps,
             (unsigned long long)distinguishedPointsFound,
             mkeysPerSec,
             progress);
      fflush(stdout);
      
      lastStatus = now;
    }
  }
  
  return false;
}

uint64_t KangarooSearch::GetTotalJumps() const {
  return totalJumps;
}

uint64_t KangarooSearch::GetDistinguishedPointsFound() const {
  return distinguishedPointsFound;
}

double KangarooSearch::GetExpectedOperations() const {
  // Ожидаемое количество операций: sqrt(rangeSize) * sqrt(pi/2)
  Int tempSize;
  tempSize.Set((Int*)&rangeSize);
  double rangeSqrt = sqrt(tempSize.ToDouble());
  double expected = rangeSqrt * sqrt(M_PI / 2.0);
  
  if (expected > 0) {
    return (totalJumps / expected) * 100.0;
  }
  
  return 0.0;
}

void KangarooSearch::PrintStatistics() const {
  time_t elapsed = time(NULL) - searchStartTime;
  
  printf("\n\n");
  printf("=== Статистика Pollard's Kangaroo ===\n");
  printf("Всего прыжков:      %llu\n", (unsigned long long)totalJumps);
  printf("Distinguished pts:  %llu\n", (unsigned long long)distinguishedPointsFound);
  printf("Время работы:       %lld сек\n", (long long)elapsed);
  
  if (elapsed > 0) {
    double mkeysPerSec = (totalJumps / 1000000.0) / elapsed;
    printf("Средняя скорость:   %.2f MKey/s\n", mkeysPerSec);
  }
  
  Int tempSize;
  tempSize.Set((Int*)&rangeSize);
  double expected = sqrt(tempSize.ToDouble()) * sqrt(M_PI / 2.0);
  double efficiency = (totalJumps / expected) * 100.0;
  printf("Эффективность:      %.2f%% от теоретической\n", efficiency);
  
  printf("=====================================\n");
}

void KangarooSearch::SetJumpDistance(int avgBits) {
  jumpDistanceBits = avgBits;
}

void KangarooSearch::SetDistinguishedBits(int bits) {
  distinguishedBits = bits;
}

void KangarooSearch::SetNumKangaroos(int tame, int wild) {
  numTameKangaroos = tame;
  numWildKangaroos = wild;
}

bool KangarooSearch::SaveState(const std::string &filename) {
  std::ofstream file(filename.c_str(), std::ios::binary);
  if (!file.is_open()) {
    printf("[Kangaroo] Ошибка: не удалось открыть %s для записи\n", filename.c_str());
    return false;
  }
  
  // Заголовок
  file << "KANGAROO_STATE_V1\n";
  file << "RangeStart=" << rangeStart.GetBase16() << "\n";
  file << "RangeEnd=" << rangeEnd.GetBase16() << "\n";
  file << "TargetPubKeyX=" << targetPubKey.x.GetBase16() << "\n";
  file << "TargetPubKeyY=" << targetPubKey.y.GetBase16() << "\n";
  file << "TotalJumps=" << totalJumps << "\n";
  file << "DPsFound=" << distinguishedPointsFound << "\n";
  file << "JumpBits=" << jumpDistanceBits << "\n";
  file << "DPBits=" << distinguishedBits << "\n";
  
  // Tame кенгуру
  file << "TameKangaroos=" << tameKangaroos.size() << "\n";
  for (size_t i = 0; i < tameKangaroos.size(); i++) {
    file << "T_PosX=" << tameKangaroos[i].position.x.GetBase16() << "\n";
    file << "T_PosY=" << tameKangaroos[i].position.y.GetBase16() << "\n";
    file << "T_Dist=" << tameKangaroos[i].distance.GetBase16() << "\n";
    file << "T_Jumps=" << tameKangaroos[i].jumps << "\n";
  }
  
  // Wild кенгуру
  file << "WildKangaroos=" << wildKangaroos.size() << "\n";
  for (size_t i = 0; i < wildKangaroos.size(); i++) {
    file << "W_PosX=" << wildKangaroos[i].position.x.GetBase16() << "\n";
    file << "W_PosY=" << wildKangaroos[i].position.y.GetBase16() << "\n";
    file << "W_Dist=" << wildKangaroos[i].distance.GetBase16() << "\n";
    file << "W_Jumps=" << wildKangaroos[i].jumps << "\n";
  }
  
  // Distinguished points
  file << "DPCount=" << distinguishedPoints.size() << "\n";
  for (const auto &pair : distinguishedPoints) {
    const DistinguishedPoint &dp = pair.second;
    Int tmpX, tmpY, tmpDist;
    tmpX.Set((Int*)&dp.position.x);
    tmpY.Set((Int*)&dp.position.y);
    tmpDist.Set((Int*)&dp.distance);
    file << "DP_Hash=" << dp.dpHash << "\n";
    file << "DP_PosX=" << tmpX.GetBase16() << "\n";
    file << "DP_PosY=" << tmpY.GetBase16() << "\n";
    file << "DP_Dist=" << tmpDist.GetBase16() << "\n";
    file << "DP_Tame=" << (dp.isTame ? "1" : "0") << "\n";
  }
  
  file << "END\n";
  file.close();
  
  printf("[Kangaroo] ✓ Состояние сохранено: %s\n", filename.c_str());
  return true;
}

bool KangarooSearch::LoadState(const std::string &filename) {
  std::ifstream file(filename.c_str());
  if (!file.is_open()) {
    printf("[Kangaroo] Файл состояния не найден: %s\n", filename.c_str());
    return false;
  }
  
  printf("[Kangaroo] Загрузка состояния из %s...\n", filename.c_str());
  
  std::string line;
  int tameCount = 0;
  int wildCount = 0;
  int dpCount = 0;
  int tameIdx = 0, wildIdx = 0, dpIdx = 0;
  
  DistinguishedPoint currentDP;
  
  while (std::getline(file, line)) {
    if (line.empty() || line == "END") continue;
    
    size_t eqPos = line.find('=');
    if (eqPos != std::string::npos) {
      std::string key = line.substr(0, eqPos);
      std::string value = line.substr(eqPos + 1);
      
      if (key == "RangeStart") {
        rangeStart.SetBase16((char*)value.c_str());
      } else if (key == "RangeEnd") {
        rangeEnd.SetBase16((char*)value.c_str());
      } else if (key == "TotalJumps") {
        totalJumps = strtoull(value.c_str(), NULL, 10);
      } else if (key == "DPsFound") {
        distinguishedPointsFound = strtoull(value.c_str(), NULL, 10);
      } else if (key == "JumpBits") {
        jumpDistanceBits = atoi(value.c_str());
      } else if (key == "DPBits") {
        distinguishedBits = atoi(value.c_str());
      } else if (key == "TameKangaroos") {
        tameCount = atoi(value.c_str());
        tameKangaroos.resize(tameCount);
      } else if (key == "WildKangaroos") {
        wildCount = atoi(value.c_str());
        wildKangaroos.resize(wildCount);
      } else if (key == "DPCount") {
        dpCount = atoi(value.c_str());
      }
      // Tame kangaroo data
      else if (key == "T_PosX" && tameIdx < tameCount) {
        tameKangaroos[tameIdx].position.x.SetBase16((char*)value.c_str());
      } else if (key == "T_PosY" && tameIdx < tameCount) {
        tameKangaroos[tameIdx].position.y.SetBase16((char*)value.c_str());
      } else if (key == "T_Dist" && tameIdx < tameCount) {
        tameKangaroos[tameIdx].distance.SetBase16((char*)value.c_str());
      } else if (key == "T_Jumps" && tameIdx < tameCount) {
        tameKangaroos[tameIdx].jumps = strtoull(value.c_str(), NULL, 10);
        tameIdx++;
      }
      // Wild kangaroo data
      else if (key == "W_PosX" && wildIdx < wildCount) {
        wildKangaroos[wildIdx].position.x.SetBase16((char*)value.c_str());
      } else if (key == "W_PosY" && wildIdx < wildCount) {
        wildKangaroos[wildIdx].position.y.SetBase16((char*)value.c_str());
      } else if (key == "W_Dist" && wildIdx < wildCount) {
        wildKangaroos[wildIdx].distance.SetBase16((char*)value.c_str());
      } else if (key == "W_Jumps" && wildIdx < wildCount) {
        wildKangaroos[wildIdx].jumps = strtoull(value.c_str(), NULL, 10);
        wildIdx++;
      }
      // Distinguished points
      else if (key == "DP_Hash") {
        currentDP.dpHash = value;
      } else if (key == "DP_PosX") {
        currentDP.position.x.SetBase16((char*)value.c_str());
      } else if (key == "DP_PosY") {
        currentDP.position.y.SetBase16((char*)value.c_str());
      } else if (key == "DP_Dist") {
        currentDP.distance.SetBase16((char*)value.c_str());
      } else if (key == "DP_Tame") {
        currentDP.isTame = (value == "1");
        distinguishedPoints[currentDP.dpHash] = currentDP;
      }
    }
  }
  
  file.close();
  
  printf("[Kangaroo] ✓ Состояние загружено\n");
  printf("[Kangaroo]   Tame кенгуру: %d\n", tameCount);
  printf("[Kangaroo]   Wild кенгуру: %d\n", wildCount);
  printf("[Kangaroo]   Distinguished points: %zu\n", (size_t)distinguishedPoints.size());
  printf("[Kangaroo]   Всего прыжков: %llu\n", (unsigned long long)totalJumps);
  
  return true;
}

