# Script to fix CUDA Visual Studio integration
# Copies CUDA build files to Visual Studio if needed

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing CUDA Visual Studio Integration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$cudaPath = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
$cudaIntegration = Join-Path $cudaPath "extras\visual_studio_integration\MSBuildExtensions"

if (-not (Test-Path $cudaIntegration)) {
    Write-Host "ERROR: CUDA Visual Studio integration not found" -ForegroundColor Red
    Write-Host "Path: $cudaIntegration" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Solution: Install CUDA Toolkit with Visual Studio integration" -ForegroundColor Yellow
    Write-Host "Or use alternative build method (build_windows_gpu.ps1)" -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: CUDA integration found at:" -ForegroundColor Green
Write-Host "   $cudaIntegration" -ForegroundColor White
Write-Host ""

# Find Visual Studio installation
$vsVersions = @("2022", "2019", "2017")
$vsEditions = @("Community", "Professional", "Enterprise", "BuildTools")

$vsFound = $false
foreach ($version in $vsVersions) {
    foreach ($edition in $vsEditions) {
        $vsPath = "C:\Program Files\Microsoft Visual Studio\$version\$edition"
        if (Test-Path $vsPath) {
            $vcPath = Get-ChildItem "$vsPath\MSBuild\Microsoft\VC" -Directory -ErrorAction SilentlyContinue | 
                      Sort-Object Name -Descending | 
                      Select-Object -First 1
            
            if ($vcPath) {
                $buildCustomizations = Join-Path $vcPath.FullName "BuildCustomizations"
                if (Test-Path $buildCustomizations) {
                    Write-Host "Found Visual Studio: $version $edition" -ForegroundColor Green
                    Write-Host "  VC Path: $($vcPath.Name)" -ForegroundColor White
                    Write-Host "  BuildCustomizations: $buildCustomizations" -ForegroundColor White
                    Write-Host ""
                    
                    # Copy CUDA files
                    Write-Host "Copying CUDA integration files..." -ForegroundColor Yellow
                    $cudaFiles = Get-ChildItem $cudaIntegration -Filter "CUDA*.props"
                    $cudaFiles += Get-ChildItem $cudaIntegration -Filter "CUDA*.targets"
                    $cudaFiles += Get-ChildItem $cudaIntegration -Filter "CUDA*.xml"
                    
                    foreach ($file in $cudaFiles) {
                        $dest = Join-Path $buildCustomizations $file.Name
                        Copy-Item $file.FullName -Destination $dest -Force
                        Write-Host "  Copied: $($file.Name)" -ForegroundColor Green
                    }
                    
                    Write-Host ""
                    Write-Host "OK: CUDA integration files copied!" -ForegroundColor Green
                    $vsFound = $true
                    break
                }
            }
        }
        if ($vsFound) { break }
    }
    if ($vsFound) { break }
}

if (-not $vsFound) {
    Write-Host "WARNING: Visual Studio not found in standard locations" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Yellow
    Write-Host "1. Find your Visual Studio installation" -ForegroundColor White
    Write-Host "2. Copy files from:" -ForegroundColor White
    Write-Host "   $cudaIntegration" -ForegroundColor Cyan
    Write-Host "3. To:" -ForegroundColor White
    Write-Host "   [VS Path]\MSBuild\Microsoft\VC\v[version]\BuildCustomizations\" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or use alternative build method:" -ForegroundColor Yellow
    Write-Host "  .\build_windows_gpu.ps1" -ForegroundColor White
    exit 1
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "CUDA integration fixed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Now you can build in Visual Studio:" -ForegroundColor Yellow
Write-Host "  Build -> Build Solution (Ctrl+Shift+B)" -ForegroundColor White
Write-Host ""
Write-Host "Or from command line:" -ForegroundColor Yellow
Write-Host "  msbuild VanitySearch.vcxproj /p:Configuration=Release /p:Platform=x64" -ForegroundColor White
Write-Host ""


