import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.container import Container
from app.main import app
from app.shipping.carrier import CarrierClient, ShippingResult

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_db():
    """Limpia órdenes y resetea reservas antes de cada test para repetibilidad."""
    container = Container()
    with container.engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE reservation_allocations, reservations, order_items, orders CASCADE"
            )
        )
        conn.execute(text("UPDATE lots SET reserved = 0"))
    yield


def test_envio_exitoso_obtiene_guia_y_marca_shipped(monkeypatch):
    """Prueba 1: Carrier normal responde con guía -> orden pasa a SHIPPED con tracking_number."""
    def mock_request_shipping(self, order_id: int):
        return ShippingResult(
            status="SHIPPED",
            shipping_status="SHIPPED",
            tracking_number="GUIA-TEST-123",
        )

    monkeypatch.setattr(CarrierClient, "request_shipping", mock_request_shipping)

    create_resp = client.post(
        "/orders",
        json={
            "customer_email": "test1@empresa.com",
            "items": [{"sku": "CAC-TAB-70", "quantity": 1}],
        },
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]
    total = create_resp.json()["total"]

    pay_resp = client.post(f"/orders/{order_id}/pay", json={"amount": total})
    assert pay_resp.status_code == 200

    ship_resp = client.post(f"/orders/{order_id}/ship")
    assert ship_resp.status_code == 200
    data = ship_resp.json()
    assert data["status"] == "SHIPPED"
    assert data["shipping_status"] == "SHIPPED"
    assert data["tracking_number"] == "GUIA-TEST-123"


def test_envio_falla_transitoria_mantiene_paid_y_pending_retry(monkeypatch):
    """Prueba 2: Carrier falla con 500 / timeout -> orden NO se pierde, queda PAID y PENDING_RETRY."""
    def mock_request_shipping_error(self, order_id: int):
        return ShippingResult(
            status="PAID",
            shipping_status="PENDING_RETRY",
            tracking_number=None,
            error="HTTP 500",
        )

    monkeypatch.setattr(CarrierClient, "request_shipping", mock_request_shipping_error)

    create_resp = client.post(
        "/orders",
        json={
            "customer_email": "test2@empresa.com",
            "items": [{"sku": "CAC-NIB", "quantity": 1}],
        },
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]
    total = create_resp.json()["total"]

    pay_resp = client.post(f"/orders/{order_id}/pay", json={"amount": total})
    assert pay_resp.status_code == 200

    ship_resp = client.post(f"/orders/{order_id}/ship")
    assert ship_resp.status_code == 200
    data = ship_resp.json()
    assert data["status"] == "PAID"
    assert data["shipping_status"] == "PENDING_RETRY"
    assert data["tracking_number"] is None


def test_envio_perecedero_proximo_a_vencer_rechaza_409():
    """Prueba 3: Producto perecedero con < 10 días de vida útil -> rechaza con 409 Conflict (SHP-03)."""
    # CAC-TRF6 (Trufas) tiene el lote L-TRF-002 con 4 días de vida restante (< 10 días requeridos)
    create_resp = client.post(
        "/orders",
        json={
            "customer_email": "test3@empresa.com",
            "items": [{"sku": "CAC-TRF6", "quantity": 1}],
        },
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]
    total = create_resp.json()["total"]

    pay_resp = client.post(f"/orders/{order_id}/pay", json={"amount": total})
    assert pay_resp.status_code == 200

    ship_resp = client.post(f"/orders/{order_id}/ship")
    assert ship_resp.status_code == 409
    assert ship_resp.json()["error"] == "perishable_expiring_soon"
