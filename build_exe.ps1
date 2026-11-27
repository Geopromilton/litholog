# Build LithoLog Studio into dist\LithoLogStudio and refresh portable\LithoLogStudio.
# Run from D:\LithoLog Studio:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv312\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing $py" }

Write-Host "1/5 Installing PyInstaller and runtime dependencies into .venv312 ..."
# pyproj is imported at start-up by the aquifer/constraints modules; pyshp and plotly are used by
# boundary import and 3D export. Without them the frozen app fails at import time.
& uv pip install --python $py pyinstaller pyproj pyshp plotly
if ($LASTEXITCODE -ne 0) { throw "Could not install PyInstaller / runtime dependencies" }

Write-Host "2/5 Building ..."
& $py -m PyInstaller --noconfirm --clean --workpath build_exe --distpath dist LithoLogStudio.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "3/5 Self-check of the fresh build ..."
$exe = Join-Path $PSScriptRoot "dist\LithoLogStudio\LithoLogStudio.exe"
$report = Join-Path $PSScriptRoot "dist\self_check.txt"
Remove-Item $report -ErrorAction SilentlyContinue
$p = Start-Process -FilePath $exe -ArgumentList "--self-check", "`"$report`"" -PassThru
if (-not $p.WaitForExit(300000)) {
    $p.Kill()
    throw "Self-check did not finish within 5 minutes and was stopped (a hidden error dialog is the usual cause)."
}
if (-not (Test-Path $report)) { throw "Self-check wrote no report (exit code $($p.ExitCode))" }
Get-Content $report
if (-not (Select-String -Path $report -Pattern "RESULT: PASS" -Quiet)) { throw "Self-check failed; portable folder left unchanged" }

Write-Host "4/5 Replacing portable\LithoLogStudio (old one kept in _archive) ..."
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
New-Item -ItemType Directory -Force -Path "_archive" | Out-Null
if (Test-Path "portable\LithoLogStudio") { Move-Item "portable\LithoLogStudio" "_archive\portable_LithoLogStudio_$stamp" }
New-Item -ItemType Directory -Force -Path "portable" | Out-Null
Copy-Item "dist\LithoLogStudio" "portable\LithoLogStudio" -Recurse

Write-Host "5/5 Refreshing the exe in the project root ..."
Copy-Item "portable\LithoLogStudio\LithoLogStudio.exe" "LithoLogStudio.exe" -Force
if (Test-Path "_internal") { Remove-Item "_internal" -Force -Recurse -ErrorAction SilentlyContinue }
cmd /c mklink /J "_internal" "portable\LithoLogStudio\_internal" | Out-Null

Write-Host "Done. Start it with LithoLogStudio.bat."
