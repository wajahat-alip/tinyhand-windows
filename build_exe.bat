@echo off
title Build WajjiTinyHandPRO.exe
cd /d "%~dp0"

set "PY_EXE=C:\Users\PC\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

echo Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building standalone WajjiTinyHandPRO.exe...
"%PY_EXE%" -m PyInstaller --clean --noconfirm WajjiTinyHandPRO.spec

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    exit /b 1
)

echo.
echo ========================================================
echo Build succeeded: %~dp0dist\WajjiTinyHandPRO.exe
echo ========================================================
