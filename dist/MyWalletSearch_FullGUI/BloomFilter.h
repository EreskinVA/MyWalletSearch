/*
 * Bloom Filter для быстрой проверки наличия элементов
 * 
 * Свойства:
 * - False positives: возможны (~0.1% при оптимальных параметрах)
 * - False negatives: НЕВОЗМОЖНЫ (математическая гарантия!)
 * 
 * Если Bloom говорит "НЕТ" → элемента точно нет
 * Если Bloom говорит "МОЖЕТ БЫТЬ" → нужно проверить в hash table
 */

#ifndef BLOOMFILTER_H
#define BLOOMFILTER_H

#include <vector>
#include <cstdint>
#include <cstring>

class BloomFilter {
public:
  // Constructor: создает Bloom Filter оптимального размера
  // numElements: ожидаемое количество элементов
  // falsePositiveRate: желаемая вероятность ложных срабатываний (0.001 = 0.1%)
  BloomFilter(size_t numElements, double falsePositiveRate = 0.001) {
    // Вычисляем оптимальный размер (в битах)
    double m = -(numElements * log(falsePositiveRate)) / (log(2) * log(2));
    numBits = (size_t)m;
    
    // Вычисляем оптимальное количество hash-функций
    numHashes = (size_t)((numBits / (double)numElements) * log(2));
    
    // Минимум 1, максимум 10 hash-функций
    if (numHashes < 1) numHashes = 1;
    if (numHashes > 10) numHashes = 10;
    
    // Выделяем память (округляем до uint64_t)
    size_t numWords = (numBits + 63) / 64;
    bits.resize(numWords, 0);
    
    printf("[BloomFilter] Создан Bloom Filter:\n");
    printf("[BloomFilter]   Элементов: %zu\n", numElements);
    printf("[BloomFilter]   Размер: %.1f MB\n", (numWords * 8) / (1024.0 * 1024.0));
    printf("[BloomFilter]   Количество hash-функций: %zu\n", numHashes);
    printf("[BloomFilter]   False positive rate: %.3f%%\n", falsePositiveRate * 100);
  }
  
  // Добавить элемент (hash160: 20 байт)
  void add(const uint8_t* hash160) {
    for (size_t i = 0; i < numHashes; i++) {
      uint64_t hash = computeHash(hash160, i);
      size_t bitIndex = hash % numBits;
      setBit(bitIndex);
    }
  }
  
  // Проверить наличие элемента
  // Возвращает:
  //   false = элемента ТОЧНО нет (100% гарантия)
  //   true  = элемент МОЖЕТ БЫТЬ есть (нужно проверить в hash table)
  bool mayContain(const uint8_t* hash160) const {
    for (size_t i = 0; i < numHashes; i++) {
      uint64_t hash = computeHash(hash160, i);
      size_t bitIndex = hash % numBits;
      if (!getBit(bitIndex)) {
        return false;  // Хотя бы один бит = 0 → точно нет
      }
    }
    return true;  // Все биты = 1 → может быть есть
  }
  
  // Получить размер в памяти
  size_t getMemoryUsage() const {
    return bits.size() * sizeof(uint64_t);
  }
  
  // Очистить все биты
  void clear() {
    for (size_t i = 0; i < bits.size(); i++) {
      bits[i] = 0;
    }
  }

private:
  std::vector<uint64_t> bits;  // Битовый массив
  size_t numBits;              // Количество бит
  size_t numHashes;            // Количество hash-функций
  
  // Установить бит
  void setBit(size_t index) {
    size_t wordIndex = index / 64;
    size_t bitIndex = index % 64;
    bits[wordIndex] |= (1ULL << bitIndex);
  }
  
  // Проверить бит
  bool getBit(size_t index) const {
    size_t wordIndex = index / 64;
    size_t bitIndex = index % 64;
    return (bits[wordIndex] & (1ULL << bitIndex)) != 0;
  }
  
  // Вычислить hash для i-й hash-функции
  // Используем простой и быстрый метод: double hashing
  // hash_i(x) = hash1(x) + i * hash2(x)
  uint64_t computeHash(const uint8_t* data, size_t i) const {
    // Hash1: используем первые 8 байт hash160
    uint64_t h1 = *((uint64_t*)data);
    
    // Hash2: используем вторые 8 байт hash160
    uint64_t h2 = *((uint64_t*)(data + 8));
    
    // Дополнительное перемешивание для лучшего распределения
    h1 ^= h1 >> 33;
    h1 *= 0xff51afd7ed558ccdULL;
    h1 ^= h1 >> 33;
    
    h2 ^= h2 >> 33;
    h2 *= 0xc4ceb9fe1a85ec53ULL;
    h2 ^= h2 >> 33;
    
    // Комбинируем: hash_i = h1 + i * h2
    return h1 + (i * h2);
  }
};

#endif // BLOOMFILTER_H

