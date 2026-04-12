#!/bin/bash
# Obtener la ruta absoluta del directorio del script principal (pm.py)
# Esto asume que pm.py y el directorio venv están en el mismo directorio que este lanzador
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
# Ruta al intérprete de Python dentro del entorno virtual
PYTHON_VENV="$SCRIPT_DIR/cryptography/bin/python"
# Ruta al script principal de Python
MAIN_SCRIPT="$SCRIPT_DIR/pm.py"

# Ejecutar el script principal con el intérprete del venv, pasando todos los argumentos
exec "$PYTHON_VENV" "$MAIN_SCRIPT" "$@"
