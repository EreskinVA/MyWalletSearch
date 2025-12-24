# Build script for VanitySearch on Windows with GPU support
# Важно:
# - CUDA 13.x НЕ поддерживает Pascal (sm_61). Для GTX 10xx используйте CUDA 11.8 (или 12.x, если поддерживает sm_61 в вашей версии).
# - По умолчанию скрипт старается сам определить GPU/CCAP и выбрать установленный CUDA Toolkit.

param(
    # Явно указать путь к CUDA Toolkit (если не задан — берём CUDA_PATH, иначе пробуем v11.8 затем v13.1)
    [Parameter(Mandatory = $false)]
    [string]$CudaPath = $env:CUDA_PATH,

    # Примеры:
    #  -CCAP 6.1  (GTX 1050 Ti / Pascal)  -> требует CUDA 11.8/12.x (CUDA 13.x не соберёт)
    #  -CCAP 8.6  (RTX 30 / Ampere)
    #  -CCAP 8.9  (RTX 40 / Ada, например 4090)
    #  -CCAP 7.5  (RTX 20 / Turing)
    [Parameter(Mandatory = $false)]
    [string]$CCAP = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building VanitySearch for Windows (GPU)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check / pick CUDA
if ([string]::IsNullOrWhiteSpace($CudaPath)) {
    $candidates = @(
        "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8",
        "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
    )
    $CudaPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

$cudaPath = $CudaPath
if (-not (Test-Path $cudaPath)) {
    Write-Host "ERROR: CUDA not found at '$cudaPath'." -ForegroundColor Red
    Write-Host "Install CUDA Toolkit (например 11.8) or set CUDA_PATH / pass -CudaPath." -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: CUDA found at $cudaPath" -ForegroundColor Green

# Check nvcc
$nvcc = Join-Path $cudaPath "bin\nvcc.exe"
if (-not (Test-Path $nvcc)) {
    Write-Host "ERROR: nvcc.exe not found" -ForegroundColor Red
    exit 1
}

Write-Host "OK: nvcc found" -ForegroundColor Green

# Check compiler
$compilerFound = $false
$compilerPath = ""

# Check MinGW
if (Test-Path "C:\msys64\mingw64\bin\g++.exe") {
    $compilerPath = "C:\msys64\mingw64\bin\g++.exe"
    $compilerFound = $true
    Write-Host "OK: MinGW (MSYS2) found" -ForegroundColor Green
} elseif (Test-Path "C:\MinGW\bin\g++.exe") {
    $compilerPath = "C:\MinGW\bin\g++.exe"
    $compilerFound = $true
    Write-Host "OK: MinGW found" -ForegroundColor Green
}

# Check Visual Studio
if (-not $compilerFound) {
    $vsPath = Get-ChildItem "C:\Program Files\Microsoft Visual Studio" -ErrorAction SilentlyContinue | 
              Where-Object { $_.Name -match "20\d\d" } | 
              Sort-Object Name -Descending | 
              Select-Object -First 1
    
    if ($vsPath) {
        $vcvars = Join-Path $vsPath.FullName "VC\Auxiliary\Build\vcvars64.bat"
        if (Test-Path $vcvars) {
            Write-Host "OK: Visual Studio found: $($vsPath.Name)" -ForegroundColor Green
            Write-Host ""
            Write-Host "To build with Visual Studio:" -ForegroundColor Yellow
            Write-Host "1. Open 'Developer Command Prompt for VS'" -ForegroundColor Yellow
            Write-Host "2. Navigate to project directory" -ForegroundColor Yellow
            Write-Host "3. Run: msbuild VanitySearch.vcxproj /p:Configuration=Release /p:Platform=x64" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Or install MinGW/MSYS2 to use Makefile" -ForegroundColor Yellow
            exit 0
        }
    }
}

if (-not $compilerFound) {
    Write-Host ""
    Write-Host "ERROR: C++ compiler not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install one of the following:" -ForegroundColor Yellow
    Write-Host "1. MSYS2 (recommended): https://www.msys2.org/" -ForegroundColor Yellow
    Write-Host "   After installation: pacman -S mingw-w64-x86_64-gcc" -ForegroundColor Yellow
    Write-Host "2. MinGW: https://sourceforge.net/projects/mingw-w64/" -ForegroundColor Yellow
    Write-Host "3. Visual Studio with C++ support" -ForegroundColor Yellow
    exit 1
}

# Detect CUDA version (best-effort)
$cudaVersion = ""
try {
    $verOut = & $nvcc --version 2>$null | Out-String
    if ($verOut -match 'release\s+(\d+)\.(\d+)') {
        $cudaVersion = "$($Matches[1]).$($Matches[2])"
    }
} catch {}

# Auto-detect CCAP if not provided
if ([string]::IsNullOrWhiteSpace($CCAP)) {
    try {
        $cc = (& nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>$null) | Select-Object -First 1
        if ($cc -match '^\s*\d+(\.\d+)?\s*$') {
            $CCAP = $cc.Trim()
        }
    } catch {}
}

if ([string]::IsNullOrWhiteSpace($CCAP)) {
    $CCAP = "8.6"  # разумный дефолт для RTX 30, если авто-детект не сработал
}

if ($CCAP -notmatch '^\d+(\.\d+)?$') {
    Write-Host "ERROR: Invalid -CCAP value '$CCAP'. Use like 6.1 / 7.5 / 8.6 / 8.9" -ForegroundColor Red
    exit 1
}

$ccap = ($CCAP -replace '\.', '')

if ($ccap -eq "61" -and $cudaVersion -ne "" -and ([version]$cudaVersion -ge [version]"13.0")) {
    Write-Host "ERROR: CCAP=6.1 (sm_61) не поддерживается в CUDA $cudaVersion." -ForegroundColor Red
    Write-Host "Решение: используйте CUDA 11.8 (рекомендуется) и соберите под sm_61, либо обновите GPU." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Build parameters:" -ForegroundColor Cyan
Write-Host "  Compute Capability: $CCAP (sm_$ccap)" -ForegroundColor White
Write-Host "  CUDA: $($cudaVersion -ne '' ? ('v' + $cudaVersion) : 'unknown')" -ForegroundColor White
Write-Host "  Compiler: $compilerPath" -ForegroundColor White
Write-Host ""

# Clean
Write-Host "Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path "obj") {
    Remove-Item -Recurse -Force "obj"
}
if (Test-Path "VanitySearch.exe") {
    Remove-Item -Force "VanitySearch.exe"
}

# Create directories
New-Item -ItemType Directory -Force -Path "obj\GPU" | Out-Null
New-Item -ItemType Directory -Force -Path "obj\hash" | Out-Null

Write-Host "OK: Directories created" -ForegroundColor Green

# Compile GPU code
Write-Host ""
Write-Host "Compiling GPU code..." -ForegroundColor Yellow
$gpuEngine = "obj\GPU\GPUEngine.o"
$gpuSource = "GPU\GPUEngine.cu"

$nvccArgs = @(
    "-maxrregcount=0",
    "--ptxas-options=-v",
    "--compile",
    "-ccbin", "`"$compilerPath`"",
    "-m64",
    "-O2",
    "-I`"$cudaPath\include`"",
    "-gencode=arch=compute_$ccap,code=sm_$ccap",
    "-o", $gpuEngine,
    "-c", $gpuSource
)

& $nvcc $nvccArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: GPU code compilation failed" -ForegroundColor Red
    exit 1
}
Write-Host "OK: GPU code compiled" -ForegroundColor Green

# Compile other files
Write-Host ""
Write-Host "Compiling source files..." -ForegroundColor Yellow

$sources = @(
    "Base58.cpp", "IntGroup.cpp", "main.cpp", "Random.cpp",
    "Timer.cpp", "Int.cpp", "IntMod.cpp", "Point.cpp", "SECP256K1.cpp",
    "Vanity.cpp", "GPU\GPUGenerate.cpp", "hash\ripemd160.cpp",
    "hash\sha256.cpp", "hash\sha512.cpp", "Bech32.cpp", "Wildcard.cpp",
    "SegmentSearch.cpp", "ProgressManager.cpp", "LoadBalancer.cpp",
    "AdaptivePriority.cpp", "KangarooSearch.cpp",
    "hash\ripemd160_sse.cpp", "hash\sha256_sse.cpp",
    "AVX512.cpp", "AVX512BatchProcessor.cpp"
)

$objects = @()
foreach ($src in $sources) {
    $obj = "obj\" + ($src -replace '\\', '\' -replace '\.cpp$', '.o')
    $objects += $obj
    
    $gppArgs = @(
        "-DWITHGPU",
        "-m64",
        "-mssse3",
        "-Wno-write-strings",
        "-O3",
        "-I.",
        "-I`"$cudaPath\include`"",
        "-o", $obj,
        "-c", $src
    )
    
    & $compilerPath $gppArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Compilation of $src failed" -ForegroundColor Red
        exit 1
    }
}

Write-Host "OK: All files compiled" -ForegroundColor Green

# Linking
Write-Host ""
Write-Host "Linking..." -ForegroundColor Yellow

$linkArgs = @(
    $objects,
    "-L`"$cudaPath\lib\x64`"",
    "-lcudart",
    "-o", "VanitySearch.exe"
)

& $compilerPath $linkArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Linking failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "OK: Build completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Executable: VanitySearch.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "To test, run:" -ForegroundColor Yellow
Write-Host '  .\VanitySearch.exe -g 32,64 -check' -ForegroundColor White
Write-Host ""
