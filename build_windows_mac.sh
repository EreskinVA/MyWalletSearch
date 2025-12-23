#!/bin/bash
# Скрипт для компиляции VanitySearch для Windows на Mac
# Требуется: brew install mingw-w64

set -e

echo "=========================================="
echo "  КРОСС-КОМПИЛЯЦИЯ ДЛЯ WINDOWS НА MAC"
echo "=========================================="
echo ""

# Проверка наличия MinGW
if ! command -v x86_64-w64-mingw32-g++ &> /dev/null; then
    echo "❌ ОШИБКА: MinGW-w64 не найден!"
    echo ""
    echo "Установите его командой:"
    echo "  brew install mingw-w64"
    echo ""
    exit 1
fi

echo "✅ MinGW-w64 найден: $(x86_64-w64-mingw32-g++ --version | head -1)"
echo ""

# Настройки компилятора
CXX=x86_64-w64-mingw32-g++
CXXFLAGS="-O3 -std=c++11 -DNOMINMAX -DWIN32_LEAN_AND_MEAN -I. -DWITHGPU"
LDFLAGS="-static-libgcc -static-libstdc++ -lpthread"

# Исходные файлы
SRC_FILES=(
    "Base58.cpp"
    "IntGroup.cpp"
    "main.cpp"
    "Random.cpp"
    "Timer.cpp"
    "Int.cpp"
    "IntMod.cpp"
    "Point.cpp"
    "SECP256K1.cpp"
    "Vanity.cpp"
    "GPU/GPUGenerate.cpp"
    "hash/ripemd160.cpp"
    "hash/sha256.cpp"
    "hash/sha512.cpp"
    "Bech32.cpp"
    "Wildcard.cpp"
    "SegmentSearch.cpp"
    "ProgressManager.cpp"
    "LoadBalancer.cpp"
    "AdaptivePriority.cpp"
    "KangarooSearch.cpp"
    "AVX512.cpp"
    "AVX512BatchProcessor.cpp"
)

TARGET="VanitySearch.exe"
OBJ_DIR="obj_win"

# Создание директории для объектных файлов
mkdir -p "$OBJ_DIR"
mkdir -p "$OBJ_DIR/GPU"
mkdir -p "$OBJ_DIR/hash"

echo "[1/3] Компиляция исходных файлов..."
for src in "${SRC_FILES[@]}"; do
    if [ ! -f "$src" ]; then
        echo "⚠️  Предупреждение: файл $src не найден, пропускаем"
        continue
    fi
    
    obj="$OBJ_DIR/${src//\//_}.o"
    echo "  Компилирую: $src"
    $CXX $CXXFLAGS -c "$src" -o "$obj" || {
        echo "❌ Ошибка компиляции: $src"
        exit 1
    }
done

echo ""
echo "[2/3] Сборка исполняемого файла..."
OBJ_FILES=("$OBJ_DIR"/*.o)
$CXX "${OBJ_FILES[@]}" $LDFLAGS -o "$TARGET" || {
    echo "❌ Ошибка линковки"
    exit 1
}

echo ""
echo "[3/3] Проверка результата..."
if [ -f "$TARGET" ]; then
    file "$TARGET"
    echo ""
    echo "=========================================="
    echo "  ✅ КОМПИЛЯЦИЯ УСПЕШНА!"
    echo "=========================================="
    echo ""
    echo "Исполняемый файл: $TARGET"
    echo ""
    echo "⚠️  ВАЖНО:"
    echo "  - CUDA не будет работать (нет NVIDIA драйверов на Mac)"
    echo "  - Используйте только CPU версию: без флагов -gpu"
    echo "  - Скопируйте .exe на Windows для использования"
    echo ""
else
    echo "❌ Ошибка: файл $TARGET не создан"
    exit 1
fi

