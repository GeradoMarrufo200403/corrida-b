import requests
from fastapi.testclient import TestClient

from app.main import app

CARRIER_SIM = "http://localhost:9100"

def set_mode(modo: str, veces: int = 1):
    resp = requests.post(f"{CARRIER_SIM}/__sim/modo", json={"modo": modo, "veces": veces})
    print(f"\n[PANEL] Activado modo='{modo}', veces={veces} (HTTP {resp.status_code})")

def reset_sim():
    requests.post(f"{CARRIER_SIM}/__sim/reiniciar")

def ship_test_order(client, customer_email):
    # 1. Crear
    c_resp = client.post("/orders", json={
        "customer_email": customer_email,
        "items": [{"sku": "CAC-TAB-70", "quantity": 1}]
    })
    order_id = c_resp.json()["id"]
    total = c_resp.json()["total"]

    # 2. Pagar
    client.post(f"/orders/{order_id}/pay", json={"amount": total})

    # 3. Ship
    s_resp = client.post(f"/orders/{order_id}/ship")
    return order_id, s_resp.status_code, s_resp.json()

def main():
    client = TestClient(app)
    reset_sim()

    print("=" * 70)
    print(" FASE 4 - TAREA B: EXPLORACIÓN DE LOS 3 MODOS DEL PANEL")
    print("=" * 70)

    # 1. Modo lento (veces=1: reintento recupera la guía con éxito)
    print("\n--- 1. PROBANDO MODO 'lento' ---")
    set_mode("lento", veces=1)
    oid, _status, data = ship_test_order(client, "lento@test.com")
    print(f"Resultado Orden {oid} -> status='{data.get('status')}', shipping_status='{data.get('shipping_status')}', tracking_number='{data.get('tracking_number')}'")

    # 2. Modo sin_guia (veces=3: proveedor responde sin guía, se preserva en PAID)
    print("\n--- 2. PROBANDO MODO 'sin_guia' ---")
    set_mode("sin_guia", veces=3)
    oid, _status, data = ship_test_order(client, "singuia@test.com")
    print(f"Resultado Orden {oid} -> status='{data.get('status')}', shipping_status='{data.get('shipping_status')}', tracking_number={data.get('tracking_number')}")

    # 3. Modo error_500 (veces=3: falla de servidor transitoria, se preserva en PAID)
    print("\n--- 3. PROBANDO MODO 'error_500' ---")
    set_mode("error_500", veces=3)
    oid, _status, data = ship_test_order(client, "err500@test.com")
    print(f"Resultado Orden {oid} -> status='{data.get('status')}', shipping_status='{data.get('shipping_status')}', tracking_number={data.get('tracking_number')}")

    reset_sim()
    print("\n" + "=" * 70)
    print(" PANEL REINICIADO A MODO NORMAL")
    print("=" * 70)

if __name__ == "__main__":
    main()
