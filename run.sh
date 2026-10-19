#!/usr/bin/env bash
# ==============================================================================
# NGL English Assistant - One-Click Master Launcher (macOS / Linux)
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=============================================================================="
echo "NGL English Assistant - Lanzador Automatizado (macOS / Linux)"
echo "=============================================================================="

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[ERROR] No se detecto instalacion de Python."
    echo "Por favor instala Python 3.10 o superior (ej: brew install python en macOS o apt install python3 en Ubuntu)."
    exit 1
fi

"$PYTHON_CMD" run.py "$@"
