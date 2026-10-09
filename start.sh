#!/usr/bin/env bash
# ==============================================================================
# NGL English Assistant - Unix Launcher (start.sh)
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Comprobar comando de python3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: No se encontró Python 3 instalado en tu sistema."
    echo "Instala Python 3.10+ para continuar."
    exit 1
fi

"$PYTHON_CMD" run.py "$@"
