/*
 * AVX-512 Batch Processor
 * High-level интерфейс для batch обработки ключей
 */

#ifndef AVX512BATCHPROCESSORH
#define AVX512BATCHPROCESSORH

#include "Int.h"
#include "Point.h"
#include "SECP256k1.h"
#include "AVX512.h"
#include <cstdint>

#define AVX512_BATCH_SIZE 8

class AVX512BatchProcessor {

public:
    AVX512BatchProcessor(Secp256K1 *secp);
    ~AVX512BatchProcessor();

    // Проверить доступность AVX-512
    bool IsAvailable() const { return avx512Available; }
    
    // Обработать batch из 8 ключей
    // Возвращает: количество найденных совпадений
    int ProcessBatch(Int baseKey, const std::vector<std::string> &targetPrefixes,
                     std::vector<Int> &foundKeys);
    
    // Включить/выключить AVX-512 (runtime)
    void Enable(bool enable);
    bool IsEnabled() const { return enabled && avx512Available; }
    
    // Статистика
    uint64_t GetBatchesProcessed() const { return batchesProcessed; }
    uint64_t GetKeysProcessed() const { return keysProcessed; }
    double GetSpeedup() const { return speedup; }
    
    void ResetStats();
    void PrintStats() const;

private:
    Secp256K1 *secp;
    bool avx512Available;
    bool enabled;
    
    // Статистика
    uint64_t batchesProcessed;
    uint64_t keysProcessed;
    double speedup;
    
    // Fallback на стандартный метод если AVX-512 недоступен
    int ProcessBatchStandard(Int baseKey, const std::vector<std::string> &targetPrefixes,
                             std::vector<Int> &foundKeys);
};

#endif // AVX512BATCHPROCESSORH

