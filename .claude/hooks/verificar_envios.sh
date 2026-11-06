#!/bin/bash
INPUT=""
if read -t 0; then
  INPUT=$(cat)
fi
# evita el bucle: si ya forzamos una continuación, dejar terminar
if echo "$INPUT" | grep -q '"stop_hook_active":\s*true'; then exit 0; fi
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
ERRORES=""

# Regla 1: la clave de idempotencia no puede cambiar entre intentos
MALA=$(grep -rnE "Idempotency-Key.*(uuid|time|random|datetime)" --include=*.py app 2>/dev/null)
[ -n "$MALA" ] && ERRORES="$ERRORES\nLa clave de idempotencia cambia entre intentos:\n$MALA\n"

# Regla 2: ninguna falla se traga en silencio
CALLADO=$(grep -rnE "except.*:[[:space:]]*pass" --include=*.py app 2>/dev/null)
[ -n "$CALLADO" ] && ERRORES="$ERRORES\nHay un except que se traga la falla:\n$CALLADO\n"

# Regla 3: las pruebas deben pasar
PYTEST_CMD="pytest"
if [ -f "../.venv/Scripts/pytest.exe" ]; then
  PYTEST_CMD="../.venv/Scripts/pytest.exe"
fi

if ! OUT=$($PYTEST_CMD -q 2>&1); then
  ERRORES="$ERRORES\nLas pruebas fallan:\n$(echo "$OUT" | tail -15)\n"
fi

if [ -n "$ERRORES" ]; then
  printf "%b" "$ERRORES" >&2
  exit 2
fi
exit 0
