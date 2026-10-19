@echo off
setlocal
title NGL English Assistant

echo ==============================================================================
echo NGL English Assistant - Lanzador Automatizado (Windows)
echo ==============================================================================

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    where py >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] No se detecto instalacion de Python.
        echo Por favor instala Python 3.10 o superior desde https://www.python.org/
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

%PYTHON_CMD% run.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] El programa se detuvo con codigo de salida %ERRORLEVEL%.
    pause
)

endlocal
