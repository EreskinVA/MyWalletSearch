# 🍎→🪟 КРОСС-КОМПИЛЯЦИЯ ДЛЯ WINDOWS НА MAC

## ✅ ДА, МОЖНО! Но с ограничениями

На Mac можно скомпилировать для Windows, но **CUDA не будет работать** (требуется NVIDIA драйвер на Windows).

---

## 🚀 СПОСОБ 1: MinGW-w64 (РЕКОМЕНДУЕТСЯ)

### Установка MinGW-w64

```bash
# Установка через Homebrew
brew install mingw-w64
```

### Компиляция для Windows

```bash
cd VanitySearch

# Очистка предыдущих сборок
make clean

# Компиляция для Windows (x64)
x86_64-w64-mingw32-g++ \
  -DWITHGPU \
  -DNOMINMAX \
  -DWIN32_LEAN_AND_MEAN \
  -O3 \
  -std=c++11 \
  -I. \
  Base58.cpp IntGroup.cpp main.cpp Random.cpp Timer.cpp \
  Int.cpp IntMod.cpp Point.cpp SECP256K1.cpp Vanity.cpp \
  GPU/GPUGenerate.cpp hash/ripemd160.cpp hash/sha256.cpp \
  hash/sha512.cpp Bech32.cpp Wildcard.cpp SegmentSearch.cpp \
  ProgressManager.cpp LoadBalancer.cpp AdaptivePriority.cpp \
  KangarooSearch.cpp AVX512.cpp AVX512BatchProcessor.cpp \
  -o VanitySearch.exe \
  -static-libgcc -static-libstdc++ \
  -lpthread

# Или используйте Makefile с кросс-компилятором
CXX=x86_64-w64-mingw32-g++ make clean all
```

**⚠️ ОГРАНИЧЕНИЯ:**
- ❌ CUDA не будет работать (нет NVIDIA драйверов на Mac)
- ✅ CPU версия будет работать
- ✅ Все оптимизации (AVX-512, Kangaroo) будут работать

---

## 🚀 СПОСОБ 2: Clang с target для Windows

### Компиляция через Clang

```bash
cd VanitySearch

# Установка target для Windows
# (требуется установка Windows SDK через Wine или вручную)

clang++ \
  --target=x86_64-pc-windows-msvc \
  -DWITHGPU \
  -DNOMINMAX \
  -DWIN32_LEAN_AND_MEAN \
  -O3 \
  -std=c++11 \
  -I. \
  [все .cpp файлы] \
  -o VanitySearch.exe
```

**⚠️ ОГРАНИЧЕНИЯ:**
- Требуется Windows SDK
- Сложнее настроить

---

## 🚀 СПОСОБ 3: Docker с Windows (СЛОЖНО)

Можно использовать Docker с Windows контейнером, но это сложно и требует лицензии Windows.

---

## 🚀 СПОСОБ 4: Виртуальная машина (ЛУЧШИЙ ВАРИАНТ)

### Использование Parallels Desktop / VMware Fusion

1. Установите Windows в виртуальной машине
2. Установите Visual Studio в Windows VM
3. Компилируйте там

**✅ ПРЕИМУЩЕСТВА:**
- Полная поддержка CUDA (если GPU передается в VM)
- Все функции работают
- Можно тестировать на Windows

---

## 📋 БЫСТРЫЙ СТАРТ: MinGW-w64

### Шаг 1: Установка

```bash
brew install mingw-w64
```

### Шаг 2: Проверка

```bash
x86_64-w64-mingw32-g++ --version
```

### Шаг 3: Компиляция (CPU версия)

```bash
cd VanitySearch

# Создайте Makefile для Windows
cat > Makefile.windows << 'EOF'
CXX = x86_64-w64-mingw32-g++
CXXFLAGS = -O3 -std=c++11 -DNOMINMAX -DWIN32_LEAN_AND_MEAN -I.
LDFLAGS = -static-libgcc -static-libstdc++ -lpthread

SRC = Base58.cpp IntGroup.cpp main.cpp Random.cpp Timer.cpp \
      Int.cpp IntMod.cpp Point.cpp SECP256K1.cpp Vanity.cpp \
      GPU/GPUGenerate.cpp hash/ripemd160.cpp hash/sha256.cpp \
      hash/sha512.cpp Bech32.cpp Wildcard.cpp SegmentSearch.cpp \
      ProgressManager.cpp LoadBalancer.cpp AdaptivePriority.cpp \
      KangarooSearch.cpp AVX512.cpp AVX512BatchProcessor.cpp

OBJ = $(SRC:.cpp=.o)
TARGET = VanitySearch.exe

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CXX) $(OBJ) $(LDFLAGS) -o $(TARGET)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET)
EOF

# Компиляция
make -f Makefile.windows clean all
```

### Шаг 4: Проверка результата

```bash
file VanitySearch.exe
# Должно показать: PE32+ executable (console) x86-64, for MS Windows
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

### Что НЕ будет работать:
- ❌ **CUDA** - требует NVIDIA драйверы (нет на Mac)
- ❌ **GPU ускорение** - только CPU версия

### Что БУДЕТ работать:
- ✅ **CPU поиск** - полностью работает
- ✅ **Kangaroo алгоритм** - работает
- ✅ **AVX-512** - работает (если CPU поддерживает)
- ✅ **Сегменты** - работают
- ✅ **Прогресс сохранение** - работает

---

## 🎯 РЕКОМЕНДАЦИЯ

**Для полной функциональности (включая GPU):**
1. Используйте **виртуальную машину** (Parallels Desktop / VMware Fusion)
2. Или компилируйте **на самом Windows компьютере**
3. Или используйте **Vast.ai** (уже настроено и работает!)

**Для CPU версии:**
- MinGW-w64 отлично подходит
- Компиляция займет ~5-10 минут
- Результат будет работать на Windows

---

## 📝 ПРИМЕР КОМАНДЫ ДЛЯ ЗАПУСКА НА WINDOWS

После компиляции, скопируйте `.exe` на Windows и запустите:

```cmd
VanitySearch.exe -seg segments_54-62_GTX1050Ti.txt -bits 71 -kangaroo -progress puzzle71_54-62.dat -autosave 600 -gpu -gpuId 0 -g 256,128 -t 4 -o PUZZLE_71_SOLUTION.txt 1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU
```

**Примечание:** Если компилировали без CUDA, уберите флаги `-gpu -gpuId 0 -g 256,128`.

---

## 🔧 АЛЬТЕРНАТИВА: Использовать уже готовый билд

Если у вас есть доступ к Windows компьютеру или Vast.ai:
- Компилируйте там (уже всё настроено!)
- Или используйте готовый `.exe` файл

---

## ❓ ВОПРОСЫ?

Если возникнут проблемы с кросскомпиляцией:
1. Проверьте версию MinGW: `x86_64-w64-mingw32-g++ --version`
2. Убедитесь, что все зависимости установлены
3. Попробуйте компилировать по одному файлу для отладки

