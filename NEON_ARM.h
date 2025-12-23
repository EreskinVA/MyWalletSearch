/*
 * ARM NEON SIMD Optimizations for Apple Silicon
 * Поддержка M1/M2/M3 и других ARM процессоров
 */

#ifndef NEON_ARM_H
#define NEON_ARM_H

#include "Int.h"
#include "Point.h"
#include <stdint.h>
#include <cstdint>

#ifdef __aarch64__
#include <arm_neon.h>

// NEON может обрабатывать 2-4 ключа параллельно (128-bit регистры)
#define NEON_BATCH_SIZE 4

// Проверка поддержки NEON (на ARM всегда доступен)
bool CheckNEONSupport();

// Вывести информацию о ARM SIMD
void PrintARMCapabilities();

class NEONOps {

public:
    NEONOps();
    ~NEONOps();

    // Batch обработка 4 ключей параллельно
    static void GenerateKeys4x(const Int &baseKey, Int keys[4]);
    
    // Параллельное вычисление хешей SHA256
    static void SHA256_4x(const uint8_t* inputs[4], size_t len, 
                          uint8_t* outputs[4]);
    
    // Параллельная проверка адресов
    static int CheckAddresses4x(const uint8_t hashes[4][20],
                                 const uint8_t target[20],
                                 int &matchIndex);
    
    // NEON модульная арифметика
    static void ModAdd4x(uint64x2_t a[2], uint64x2_t b[2],
                         uint64x2_t result[2], uint64x2_t mod[2]);
    
    // Быстрое сравнение с использованием NEON
    static bool FastCompare(const uint8_t* a, const uint8_t* b, size_t len);

private:
    static bool initialized;
    static void Initialize();
};

class NEONBatchProcessor {

public:
    NEONBatchProcessor();
    ~NEONBatchProcessor();

    // Проверить доступность NEON
    bool IsAvailable() const { return neonAvailable; }
    
    // Обработать batch из 4 ключей
    int ProcessBatch(Int baseKey, const std::vector<std::string> &targetPrefixes,
                     std::vector<Int> &foundKeys);
    
    // Статистика
    uint64_t GetBatchesProcessed() const { return batchesProcessed; }
    uint64_t GetKeysProcessed() const { return keysProcessed; }
    
    void PrintStats() const;

private:
    bool neonAvailable;
    uint64_t batchesProcessed;
    uint64_t keysProcessed;
};

#else
// ARM NEON не доступен (x86 архитектура)

inline bool CheckNEONSupport() { return false; }
inline void PrintARMCapabilities() { 
    printf("[NEON] Не доступен (x86 архитектура)\n"); 
}

#endif // __aarch64__

#endif // NEON_ARM_H

