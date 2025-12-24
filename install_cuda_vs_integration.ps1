# Script to automatically install CUDA Visual Studio integration
# This will copy CUDA integration files to Visual Studio

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing CUDA Visual Studio Integration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$cudaPath = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
$cudaIntegration = Join-Path $cudaPath "extras\visual_studio_integration\MSBuildExtensions"

if (-not (Test-Path $cudaIntegration)) {
    Write-Host "ERROR: CUDA integration files not found!" -ForegroundColor Red
    Write-Host "Path: $cudaIntegration" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "CUDA Toolkit may not have Visual Studio integration installed." -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: CUDA integration files found at:" -ForegroundColor Green
Write-Host "   $cudaIntegration" -ForegroundColor White
Write-Host ""

# Find Visual Studio installations
$vsSearchPaths = @(
    "C:\Program Files\Microsoft Visual Studio",
    "C:\Program Files (x86)\Microsoft Visual Studio"
)

$vsVersions = @("2022", "2019", "2017")
$vsEditions = @("Community", "Professional", "Enterprise", "BuildTools")

$installed = @()

foreach ($searchPath in $vsSearchPaths) {
    if (Test-Path $searchPath) {
        foreach ($version in $vsVersions) {
            foreach ($edition in $vsEditions) {
                $vsPath = Join-Path $searchPath "$version\$edition"
                if (Test-Path $vsPath) {
                    $msbuildPath = Join-Path $vsPath "MSBuild\Microsoft\VC"
                    if (Test-Path $msbuildPath) {
                        $vcVersions = Get-ChildItem $msbuildPath -Directory -ErrorAction SilentlyContinue
                        foreach ($vcVersion in $vcVersions) {
                            $buildCustom = Join-Path $vcVersion.FullName "BuildCustomizations"
                            if (Test-Path $buildCustom) {
                                $installed += @{
                                    Path = $buildCustom
                                    VSVersion = $version
                                    Edition = $edition
                                    VCVersion = $vcVersion.Name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

if ($installed.Count -eq 0) {
    Write-Host "ERROR: Visual Studio BuildCustomizations directories not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Visual Studio with C++ support first." -ForegroundColor Yellow
    exit 1
}

Write-Host "Found Visual Studio installations:" -ForegroundColor Green
foreach ($install in $installed) {
    Write-Host "  $($install.VSVersion) $($install.Edition) - VC $($install.VCVersion)" -ForegroundColor White
    Write-Host "    Path: $($install.Path)" -ForegroundColor Gray
}
Write-Host ""

# Copy CUDA files
Write-Host "Copying CUDA integration files..." -ForegroundColor Yellow

$cudaFiles = @()
$cudaFiles += Get-ChildItem $cudaIntegration -Filter "CUDA*.props" -ErrorAction SilentlyContinue
$cudaFiles += Get-ChildItem $cudaIntegration -Filter "CUDA*.targets" -ErrorAction SilentlyContinue
$cudaFiles += Get-ChildItem $cudaIntegration -Filter "CUDA*.xml" -ErrorAction SilentlyContinue

if ($cudaFiles.Count -eq 0) {
    Write-Host "ERROR: No CUDA integration files found!" -ForegroundColor Red
    exit 1
}

Write-Host "Files to copy:" -ForegroundColor Cyan
foreach ($file in $cudaFiles) {
    Write-Host "  $($file.Name)" -ForegroundColor White
}
Write-Host ""

$copiedCount = 0
foreach ($install in $installed) {
    Write-Host "Installing to: $($install.VSVersion) $($install.Edition) (VC $($install.VCVersion))" -ForegroundColor Yellow
    
    foreach ($file in $cudaFiles) {
        $dest = Join-Path $install.Path $file.Name
        try {
            Copy-Item $file.FullName -Destination $dest -Force
            Write-Host "  OK: $($file.Name)" -ForegroundColor Green
            $copiedCount++
        } catch {
            Write-Host "  ERROR: Failed to copy $($file.Name)" -ForegroundColor Red
            Write-Host "    $($_.Exception.Message)" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Copied $copiedCount file(s) to $($installed.Count) Visual Studio installation(s)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now you can build the project in Visual Studio:" -ForegroundColor Yellow
Write-Host "  1. Open VanitySearch.sln or VanitySearch.vcxproj" -ForegroundColor White
Write-Host "  2. Select configuration: Release" -ForegroundColor White
Write-Host "  3. Select platform: x64" -ForegroundColor White
Write-Host "  4. Build -> Build Solution (Ctrl+Shift+B)" -ForegroundColor White
Write-Host ""


