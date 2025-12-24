# Финальные исправления для Visual Studio

## Выполнено

1. ✅ **Файлы CUDA integration скопированы в VS 18**
   - Путь: `C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Microsoft\VC\v180\BuildCustomizations`
   - Файлы: CUDA 13.1.props, CUDA 13.1.targets, CUDA 13.1.xml, CUDA 13.1.Version.props

2. ✅ **Добавлен CodeGeneration в ItemDefinitionGroup**
   - Для всех конфигураций: Debug, Release, ReleaseSM30
   - Формат: `compute_61,sm_61`

3. ✅ **Настроены параметры CUDA**
   - MaxRegCount: 0
   - Optimization: O2
   - TargetMachinePlatform: 64

## Проблема с командой nvcc

Если все еще видите ошибку с неправильным форматом `-gencode`:
`-gencode=arch=compute_61,code=\"sm_61,compute_61\"`

Это может быть из-за того, что Visual Studio неправильно интерпретирует CodeGeneration.

### Решение 1: Очистить кэш сборки

1. В Visual Studio: Build → Clean Solution
2. Удалите папки: `x64\Release`, `x64\Debug`
3. Build → Rebuild Solution

### Решение 2: Использовать AdditionalCompilerOptions

Если проблема остается, можно явно указать параметры компиляции через AdditionalCompilerOptions.

### Решение 3: Альтернативная сборка

Если Visual Studio все еще не работает, используйте PowerShell скрипт:

```powershell
.\build_windows_gpu.ps1
```

Этот скрипт собирает проект напрямую через nvcc без Visual Studio integration.

## Проверка после сборки

После успешной сборки:

```powershell
cd x64\Release
.\VanitySearch.exe -g 32,64 -check
```

Если видите ошибку OOM, уменьшите grid:
```powershell
.\VanitySearch.exe -g 16,64 -check
```

## Тестовый запуск

```powershell
.\VanitySearch.exe -gpu -gpuId 0 -g 32,64 -t 2 -m 2000000 -o test.txt "1P*X"
```


