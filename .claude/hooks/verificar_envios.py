#!/usr/bin/env python3
import os
import re
import subprocess
import sys


def main():
    errores = []

    # Regla 1: la clave de idempotencia no puede cambiar entre intentos
    bad_key_pattern = re.compile(r"Idempotency-Key.*(uuid|time|random|datetime)")
    # Regla 2: ninguna falla se traga en silencio
    pass_pattern = re.compile(r"except.*:\s*pass")

    for root, _, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        if bad_key_pattern.search(line):
                            errores.append(f"La clave de idempotencia cambia entre intentos en {path}:{line_num}:\n  {line.strip()}")
                        if pass_pattern.search(line):
                            errores.append(f"Hay un except que se traga la falla en {path}:{line_num}:\n  {line.strip()}")

    # Regla 3: las pruebas deben pasar
    pytest_bin = os.path.join("..", ".venv", "Scripts", "pytest.exe")
    cmd = [pytest_bin if os.path.exists(pytest_bin) else "pytest", "-q"]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        lines = (proc.stdout + proc.stderr).strip().splitlines()
        tail = "\n".join(lines[-15:])
        errores.append(f"Las pruebas fallan:\n{tail}")

    if errores:
        for err in errores:
            sys.stderr.write(f"\n[ERROR HOOK] {err}\n")
        print("\nResultado: CÓDIGO DE SALIDA 2 (BLOQUEADO)")
        sys.exit(2)

    print("\nResultado: CÓDIGO DE SALIDA 0 (TODO CORRECTO)")
    sys.exit(0)

if __name__ == "__main__":
    main()
