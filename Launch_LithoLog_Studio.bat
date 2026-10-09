@echo off
setlocal
cd /d "%~dp0"
title LithoLog Studio - Open-Source Geotechnical, Hydrogeology & Mining Platform

echo =====================================================================
echo Launching LithoLog Studio (RockWorks + GMS + Surpac Unified Desktop)
echo Location: %~dp0portable\LithoLogStudio\LithoLogStudio.exe
echo =====================================================================

if exist "portable\LithoLogStudio\LithoLogStudio.exe" (
    start "" "portable\LithoLogStudio\LithoLogStudio.exe" %*
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m litholog.studio %*
    exit /b 0
)

echo ERROR: Could not find portable executable or virtual environment.
pause
