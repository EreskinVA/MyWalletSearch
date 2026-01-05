/*
 * AVX-512 SIMD Optimizations
 * Обработка 8 ключей параллельно
 * Требует: Intel Skylake-X, Ice Lake, AMD Zen 4+ или новее
 */

#ifndef AVX512H
#define AVX512H

#include "Int.h"
#include "Point.h"
#include <immintrin.h>
#include <stdint.h>
#include <cstdint>

// Проверка поддержки AVX-512 на runtime
bool CheckAVX512Support();

// Вывести информацию о SIMD возможностях CPU
void PrintSIMDCapabilities();

#ifdef __AVX512F__

// AVX-512 включен при компиляции

// Структура для batch обработки 8 ключей
typedef struct {
    __m512i bits64[NB64BLOCK];  // 5 блоков по 512 бит = 8 Int'ов
} Int8x;

// Структура для 8 точек эллиптической кривой
typedef struct {
    __m512i x[NB64BLOCK];  // X координаты
    __m512i y[NB64BLOCK];  // Y координаты
} Point8x;

class AVX512Ops {

public:
    AVX512Ops();
    ~AVX512Ops();

    // Batch обработка ключей
    static void GenerateKeys8x(const Int &baseKey, Int keys[8]);
    
    // Параллельное вычисление публичных ключей (основная оптимизация)
    static void ComputePublicKeys8x(const Int keys[8], Point points[8]);
    
    // Параллельное вычисление хешей (SHA256 + RIPEMD160)
    static void ComputeHashes8x(const Point points[8], uint8_t hashes[8][20]);
    
    // Параллельная проверка адресов
    static int CheckAddresses8x(const uint8_t hashes[8][20], 
                                 const uint8_t target[20],
                                 int &matchIndex);
    
    // SIMD модульная арифметика (внутренние функции)
    static void ModAdd8x(__m512i a[NB64BLOCK], __m512i b[NB64BLOCK], 
                         __m512i result[NB64BLOCK], __m512i mod[NB64BLOCK]);
    
    static void ModMul8x(__m512i a[NB64BLOCK], __m512i b[NB64BLOCK],
                         __m512i result[NB64BLOCK], __m512i mod[NB64BLOCK]);
    
    // SHA256 для 8 входов параллельно
    static void SHA256_8x(const uint8_t* inputs[8], size_t len, 
                          uint8_t* outputs[8]);
    
    // RIPEMD160 для 8 входов параллельно
    static void RIPEMD160_8x(const uint8_t* inputs[8], size_t len,
                             uint8_t* outputs[8]);

private:
    // Вспомогательные SIMD операции
    static __m512i LoadInt(const Int &value);
    static void StoreInt(__m512i simd, Int &value);
    
    // Векторизованные константы
    static __m512i secp256k1_p;
    static __m512i secp256k1_n;
    static __m512i secp256k1_gx;
    static __m512i secp256k1_gy;
    
    static bool initialized;
    static void Initialize();
};

#else
// AVX-512 не доступен - заглушки

class AVX512Ops {
public:
    static bool IsAvailable() { return false; }
};

#endif // __AVX512F__

#endif // AVX512H

