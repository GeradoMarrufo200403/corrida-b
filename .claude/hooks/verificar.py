#!/usr/bin/env python3
import datetime
import os
import subprocess
import sys

LOG_FILE = os.path.join(".claude", "verificacion.log")
LOOP_FILE = os.path.join(".claude", ".loop_counter")
SUITE = os.path.join("tests", "test_precios_escudo.py")

os.makedirs(".claude", exist_ok=True)

# 1. Requisito de evitar bucle infinito
count = 0
if os.path.exists(LOOP_FILE):
    try:
        with open(LOOP_FILE, "r") as f:
            count = int(f.read().strip())
    except Exception:  # noqa: BLE001
        count = 0

now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if count >= 2:
    with open(LOOP_FILE, "w") as f:
        f.write("0")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now_str} | PASO (continuacion forzada)\n")
    sys.exit(0)

# 2. Ejecutar ruff check . y pytest -q tests/test_precios_escudo.py
ruff_cmd = ["ruff", "check", "."]
pytest_cmd = ["pytest", "-q", SUITE]

# Buscar en venv si están disponibles
venv_scripts = os.path.join("..", ".venv", "Scripts")
if os.path.isdir(venv_scripts):
    r_exe = os.path.join(venv_scripts, "ruff.exe")
    p_exe = os.path.join(venv_scripts, "pytest.exe")
    if os.path.exists(r_exe):
        ruff_cmd[0] = r_exe
    if os.path.exists(p_exe):
        pytest_cmd[0] = p_exe

proc_ruff = subprocess.run(ruff_cmd, check=False, capture_output=True, text=True)
proc_pytest = subprocess.run(pytest_cmd, check=False, capture_output=True, text=True)

combined_output = proc_ruff.stdout + proc_ruff.stderr + "\n" + proc_pytest.stdout + proc_pytest.stderr

if proc_ruff.returncode == 0 and proc_pytest.returncode == 0:
    with open(LOOP_FILE, "w") as f:
        f.write("0")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now_str} | PASO\n")
    print("Hook: Verificacion completada exitosamente.")
    sys.exit(0)
else:
    count += 1
    with open(LOOP_FILE, "w") as f:
        f.write(str(count))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now_str} | BLOQUEO\n")

    # Enviar las últimas 30 líneas a stderr
    lines = combined_output.strip().splitlines()
    last_30 = lines[-30:] if len(lines) > 30 else lines
    sys.stderr.write("\n".join(last_30) + "\n")
    sys.exit(2)
