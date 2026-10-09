@echo off
setlocal
title NGL English Assistant

echo ==============================================================================
echo  🎓 NGL English Assistant - Iniciando sistema...
echo ==============================================================================

cd /d "%~dp0"

REM Comprobar si python esta instalado
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python en el PATH del sistema.
    echo Por favor, instala Python 3.10 o superior desde https://www.python.org/
    echo Asegurate de marcar la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

REM Ejecutar el orquestador principal (acepta flags como --browser brave u --browser opera)
python run.py %*

if %errorlevel% neq 0 (
    echo.
    echo [AVISO] El asistente finalizo con codigo de error %errorlevel%.
    pause
)
