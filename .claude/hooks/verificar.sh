#!/usr/bin/env bash
# ==============================================================================
# Hook Stop para Claude Code
# 
# Requisitos:
# 1. Ejecutar ruff check . y únicamente tests/test_precios_escudo.py.
# 2. Si algo falla, bloquear devolviendo las últimas 30 líneas por stderr y salir con código 2.
# 3. Evitar bucles infinitos: tras más de 2 fallos consecutivos, permitir pasar con código 0.
# 4. Registrar en .claude/verificacion.log fecha y hora | PASO o | BLOQUEO.
# ==============================================================================

LOG_FILE=".claude/verificacion.log"
COUNTER_FILE=".claude/.loop_counter"
SUITE="tests/test_precios_escudo.py"

mkdir -p .claude

# Determinar ejecutables de ruff y pytest (PATH del sistema o entorno virtual)
RUFF_CMD="ruff"
PYTEST_CMD="pytest"

if ! command -v ruff >/dev/null 2>&1; then
    if [ -f "../.venv/Scripts/ruff.exe" ]; then
        RUFF_CMD="../.venv/Scripts/ruff.exe"
    elif [ -f ".venv/Scripts/ruff.exe" ]; then
        RUFF_CMD=".venv/Scripts/ruff.exe"
    elif [ -f ".venv/bin/ruff" ]; then
        RUFF_CMD=".venv/bin/ruff"
    fi
fi

if ! command -v pytest >/dev/null 2>&1; then
    if [ -f "../.venv/Scripts/pytest.exe" ]; then
        PYTEST_CMD="../.venv/Scripts/pytest.exe"
    elif [ -f ".venv/Scripts/pytest.exe" ]; then
        PYTEST_CMD=".venv/Scripts/pytest.exe"
    elif [ -f ".venv/bin/pytest" ]; then
        PYTEST_CMD=".venv/bin/pytest"
    fi
fi

# 3. Mecanismo contra bucles infinitos
COUNTER=0
if [ -f "$COUNTER_FILE" ]; then
    COUNTER=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
fi

NOW=$(date "+%Y-%m-%d %H:%M:%S")

if [ "$COUNTER" -ge 2 ]; then
    echo 0 > "$COUNTER_FILE"
    echo "$NOW | PASO" >> "$LOG_FILE"
    exit 0
fi

# 1. Ejecutar ruff check . y únicamente la suite del escudo
OUTPUT_FILE=$(mktemp)

$RUFF_CMD check . > "$OUTPUT_FILE" 2>&1
RUFF_EXIT=$?

$PYTEST_CMD -q "$SUITE" >> "$OUTPUT_FILE" 2>&1
PYTEST_EXIT=$?

# Evaluar resultados
if [ $RUFF_EXIT -eq 0 ] && [ $PYTEST_EXIT -eq 0 ]; then
    echo 0 > "$COUNTER_FILE"
    echo "$NOW | PASO" >> "$LOG_FILE"
    rm -f "$OUTPUT_FILE"
    exit 0
else
    COUNTER=$((COUNTER + 1))
    echo "$COUNTER" > "$COUNTER_FILE"
    echo "$NOW | BLOQUEO" >> "$LOG_FILE"

    # 2. Bloquear devolviendo las últimas 30 líneas por stderr y salir con código 2
    tail -n 30 "$OUTPUT_FILE" >&2
    rm -f "$OUTPUT_FILE"
    exit 2
fi
