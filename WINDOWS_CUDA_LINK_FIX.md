# 🔧 Исправление ошибки линковки CUDA (cudart_static.lib)

## Ошибка
```
LNK1181: не удается открыть входной файл "cudart_static.lib"
```

## ✅ Решение 1: Проверьте установку CUDA

1. **Убедитесь, что CUDA установлена:**
   - Проверьте наличие: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\lib\x64\cudart_static.lib`
   - Или: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.x\lib\x64\cudart_static.lib`

2. **Установите CUDA Toolkit, если его нет:**
   - Скачайте с [nvidia.com/cuda](https://developer.nvidia.com/cuda-downloads)
   - Выберите версию для Windows x86_64
   - После установки перезапустите Visual Studio

## ✅ Решение 2: Настройте пути в Visual Studio

1. Откройте проект в Visual Studio
2. **Project → Properties → Linker → General → Additional Library Directories**
3. Добавьте путь к библиотекам CUDA:
   ```
   C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3\lib\x64
   ```
   (Замените `v12.3` на вашу версию CUDA)

4. **Или через переменную окружения:**
   - Создайте/измените переменную окружения `CUDA_PATH`:
   ```
   CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3
   ```
   - Перезапустите Visual Studio

## ✅ Решение 3: Сборка без CUDA (CPU-only)

Если CUDA не установлена, можно временно убрать зависимость:

1. В `VanitySearch.vcxproj` найдите все вхождения `cudart_static.lib`
2. Удалите их из `<AdditionalDependencies>`
3. Убедитесь, что `WITHGPU` не определен в препроцессоре для Debug конфигурации
4. Удалите или закомментируйте файл `GPU\GPUEngine.cu` из проекта

**⚠️ Внимание:** Это отключит GPU ускорение, проект будет работать только на CPU.

## ✅ Решение 4: Проверьте CUDA Integration для Visual Studio

1. Убедитесь, что установлен **CUDA Toolkit** с поддержкой Visual Studio
2. Проверьте наличие файлов:
   - `C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\MSBuild\Microsoft\VC\v170\BuildCustomizations\CUDA *.props`
   - `C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\MSBuild\Microsoft\VC\v170\BuildCustomizations\CUDA *.targets`

3. Если файлов нет, установите **CUDA Toolkit** заново с опцией "Visual Studio Integration"

## 🔍 Проверка

После применения решения, попробуйте:
1. **Clean Solution** (Build → Clean Solution)
2. **Rebuild Solution** (Build → Rebuild Solution)

Если ошибка сохраняется, проверьте Output окно Visual Studio - там должны быть пути, где линкер ищет библиотеки.

