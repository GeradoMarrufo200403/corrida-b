import json

from fastapi.testclient import TestClient

from app.main import app


def main():
    client = TestClient(app)

    # 1. Crear orden con producto no perecedero
    create_resp = client.post('/orders', json={
        'customer_email': 'cliente@merida.com',
        'items': [{'sku': 'CAC-TAB-70', 'quantity': 1}]
    })
    order_data = create_resp.json()
    order_id = order_data['id']
    total = order_data['total']

    # 2. Pagar la orden
    client.post(f'/orders/{order_id}/pay', json={'amount': total})

    # 3. Llamar al endpoint de envío
    ship_resp = client.post(f'/orders/{order_id}/ship')

    print("\n" + "="*70)
    print(f" LLAMADA EXITOSA: POST /orders/{order_id}/ship")
    print("="*70)
    print(f"HTTP Status: {ship_resp.status_code} OK")
    print("Respuesta completa:")
    print(json.dumps(ship_resp.json(), indent=2))
    print("="*70)

if __name__ == '__main__':
    main()
