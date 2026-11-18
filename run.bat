@echo off
title TinyHand Windows
cd /d "%~dp0"

set "PY_EXE=C:\Users\PC\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

if exist "%PY_EXE%" (
    echo Starting TinyHand Windows with virtual environment Python...
    "%PY_EXE%" main.py
) else (
    echo Starting TinyHand Windows with system Python...
    python main.py
)

if errorlevel 1 (
    echo.
    echo ========================================================
    echo TinyHand encountered an error. See the error above.
    echo ========================================================
    pause
)
