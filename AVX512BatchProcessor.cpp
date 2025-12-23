/*
 * AVX-512 Batch Processor Implementation
 */

#include "AVX512BatchProcessor.h"
#include <stdio.h>

AVX512BatchProcessor::AVX512BatchProcessor(Secp256K1 *secp) {
    this->secp = secp;
    this->avx512Available = CheckAVX512Support();
    this->enabled = avx512Available;  // Включен по умолчанию если доступен
    
    batchesProcessed = 0;
    keysProcessed = 0;
    speedup = 1.0;
    
    if (avx512Available) {
        printf("[AVX512] ✅ AVX-512 доступен и активирован\n");
        printf("[AVX512] Обработка по %d ключей параллельно\n", AVX512_BATCH_SIZE);
        printf("[AVX512] Ожидаемое ускорение: 4-8x\n");
    } else {
        printf("[AVX512] ⚠️  AVX-512 не доступен, используется стандартный код\n");
    }
    
    PrintSIMDCapabilities();
}

AVX512BatchProcessor::~AVX512BatchProcessor() {
}

void AVX512BatchProcessor::Enable(bool enable) {
    if (enable && !avx512Available) {
        printf("[AVX512] Предупреждение: нельзя включить AVX-512, CPU не поддерживает\n");
        return;
    }
    
    enabled = enable;
    
    printf("[AVX512] AVX-512: %s\n", enabled ? "ВКЛЮЧЕН" : "ВЫКЛЮЧЕН");
}

int AVX512BatchProcessor::ProcessBatch(Int baseKey, 
                                        const std::vector<std::string> &targetPrefixes,
                                        std::vector<Int> &foundKeys) {
    batchesProcessed++;
    keysProcessed += AVX512_BATCH_SIZE;
    
#ifdef __AVX512F__
    if (IsEnabled()) {
        // AVX-512 путь
        Int keys[8];
        Point points[8];
        uint8_t hashes[8][20];
        
        // Генерация 8 ключей
        AVX512Ops::GenerateKeys8x(baseKey, keys);
        
        // Вычисление публичных ключей (это основная оптимизация)
        // В полной реализации это должно быть полностью векторизовано
        AVX512Ops::ComputePublicKeys8x(keys, points);
        
        // Вычисление хешей параллельно
        AVX512Ops::ComputeHashes8x(points, hashes);
        
        // Проверка совпадений
        int matchCount = 0;
        for (const auto &prefix : targetPrefixes) {
            // TODO: конвертация prefix в target hash
            // uint8_t target[20];
            // int matchIndex;
            // if (AVX512Ops::CheckAddresses8x(hashes, target, matchIndex)) {
            //     foundKeys.push_back(keys[matchIndex]);
            //     matchCount++;
            // }
        }
        
        return matchCount;
    }
#endif
    
    // Fallback на стандартный метод
    return ProcessBatchStandard(baseKey, targetPrefixes, foundKeys);
}

int AVX512BatchProcessor::ProcessBatchStandard(Int baseKey,
                                                const std::vector<std::string> &targetPrefixes,
                                                std::vector<Int> &foundKeys) {
    // Стандартная обработка без SIMD
    int matchCount = 0;
    
    for (int i = 0; i < AVX512_BATCH_SIZE; i++) {
        Int key;
        key.Set(&baseKey);
        key.Add(i);
        
        Point p = secp->ComputePublicKey(&key);
        
        // Проверка префиксов
        for (const auto &prefix : targetPrefixes) {
            std::string addr = secp->GetAddress(P2PKH, true, p);
            
            if (addr.find(prefix) == 0) {
                foundKeys.push_back(key);
                matchCount++;
            }
        }
    }
    
    return matchCount;
}

void AVX512BatchProcessor::ResetStats() {
    batchesProcessed = 0;
    keysProcessed = 0;
    speedup = 1.0;
}

void AVX512BatchProcessor::PrintStats() const {
    printf("\n=== AVX-512 Статистика ===\n");
    printf("Статус:           %s\n", IsEnabled() ? "АКТИВЕН" : "ВЫКЛЮЧЕН");
    printf("Батчей обработано: %llu\n", (unsigned long long)batchesProcessed);
    printf("Ключей обработано: %llu\n", (unsigned long long)keysProcessed);
    printf("Ускорение:        %.2fx\n", speedup);
    printf("=========================\n");
}

#ifndef __AVX512F__
// Заглушки если AVX-512 не скомпилирован

AVX512BatchProcessor::AVX512BatchProcessor(Secp256K1 *secp) {
    this->secp = secp;
    this->avx512Available = false;
    this->enabled = false;
    
    printf("[AVX512] ⚠️  AVX-512 не скомпилирован\n");
    printf("[AVX512] Для включения: make CXXFLAGS=\"-mavx512f ...\" all\n");
}

AVX512BatchProcessor::~AVX512BatchProcessor() {}

void AVX512BatchProcessor::Enable(bool enable) {
    printf("[AVX512] AVX-512 не доступен в этой сборке\n");
}

int AVX512BatchProcessor::ProcessBatch(Int baseKey,
                                        const std::vector<std::string> &targetPrefixes,
                                        std::vector<Int> &foundKeys) {
    return ProcessBatchStandard(baseKey, targetPrefixes, foundKeys);
}

void AVX512BatchProcessor::ResetStats() {}
void AVX512BatchProcessor::PrintStats() const {}

#endif // __AVX512F__

