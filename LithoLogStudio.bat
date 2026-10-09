@echo off
setlocal
cd /d "%~dp0"
title LithoLog Studio

if exist "portable\LithoLogStudio\LithoLogStudio.exe" (
    start "" "portable\LithoLogStudio\LithoLogStudio.exe" %*
    exit /b 0
)

if exist "LithoLogStudio.exe" (
    start "" "LithoLogStudio.exe" %*
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m litholog.studio %*
    exit /b 0
)

python -m litholog.studio %*
