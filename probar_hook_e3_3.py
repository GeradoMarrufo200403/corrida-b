import os
import subprocess

CARRIER_FILE = os.path.join("app", "shipping", "carrier.py")
HOOK_SCRIPT = os.path.join(".claude", "hooks", "verificar_envios.sh")
BASH_EXE = r"C:\Program Files\Git\bin\bash.exe" if os.path.exists(r"C:\Program Files\Git\bin\bash.exe") else "bash"

def run_hook():
    res = subprocess.run([BASH_EXE, HOOK_SCRIPT], check=False, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def main():
    print("=" * 70)
    print(" PRUEBA A MANO DEL HOOK (verificar_envios.sh)")
    print("=" * 70)

    with open(CARRIER_FILE, "r", encoding="utf-8") as f:
        original_content = f.read()

    try:
        # --- PRUEBA 1: Inyectar clave dinámica con uuid4() ---
        print("\n[1] Inyectando clave inestable con uuid4() en app/shipping/carrier.py...")
        tampered_content = original_content.replace(
            '"Idempotency-Key": f"envio-{order_id}",',
            '"Idempotency-Key": f"envio-{uuid.uuid4()}",'
        )
        with open(CARRIER_FILE, "w", encoding="utf-8") as f:
            f.write(tampered_content)

        code_1, out_1, err_1 = run_hook()
        print("Salida del hook:")
        if err_1:
            print(err_1.strip())
        if out_1:
            print(out_1.strip())
        print(f"--> CÓDIGO DE SALIDA: {code_1} (BLOQUEO CONFIRMADO)")
        assert code_1 == 2, f"Se esperaba código 2 pero dio {code_1}"

        # --- PRUEBA 2: Restaurar clave determinista ---
        print("\n[2] Restaurando clave determinista 'envio-{order_id}'...")
        with open(CARRIER_FILE, "w", encoding="utf-8") as f:
            f.write(original_content)

        code_2, out_2, err_2 = run_hook()
        print("Salida del hook:")
        if err_2:
            print(err_2.strip())
        if out_2:
            print(out_2.strip())
        print(f"--> CÓDIGO DE SALIDA: {code_2} (PASO EXITOSO)")
        assert code_2 == 0, f"Se esperaba código 0 pero dio {code_2}"

    finally:
        # Asegurar que siempre queda restaurado
        with open(CARRIER_FILE, "w", encoding="utf-8") as f:
            f.write(original_content)

    print("\n" + "=" * 70)
    print(" VERIFICACIÓN COMPLETADA: El hook protege contra claves inestables")
    print("=" * 70)

if __name__ == "__main__":
    main()
