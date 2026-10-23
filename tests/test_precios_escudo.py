from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.container import Container
from app.orders.models import OrderStatus
from app.pricing.calculator import PricedItem, calculate_total, money
from app.shared.clock import FixedClock
from app.shared.errors import Conflict
from app.shared.schemas import LineIn


@pytest.fixture(autouse=True)
def _clean_db():
    container = Container()
    with container.engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE reservation_allocations, reservations, order_items, orders CASCADE"
            )
        )
        conn.execute(text("UPDATE lots SET reserved = 0"))
    yield


# --- CAPA 1: EL ESCUDO (MÁXIMO 8 PRUEBAS) ---


def test_volumen_limite_exacto_500_sin_descuento():
    """Regla: Descuento por volumen (> 500 aplica 10%, == 500 no recibe). Tipo: unitaria.
    Detectaría: cambiar > 500 por >= 500 aplicando descuento indebido en 500.00.
    """
    items = [PricedItem(sku="CAC-TAB-70", quantity=5, unit_price=Decimal("100.00"))]
    breakdown = calculate_total(items, "cliente@normal.com")

    assert breakdown.subtotal == Decimal("500.00")
    assert breakdown.volume_discount == Decimal("0.00")
    assert breakdown.total == Decimal("500.00")


def test_volumen_supera_500_aplica_10_porciento():
    """Regla: Descuento por volumen (> 500 aplica 10%). Tipo: unitaria.
    Detectaría: no aplicar descuento en el límite superior inmediato 500.01 o requerir un umbral mayor.
    """
    items = [PricedItem(sku="CAC-BEB", quantity=1, unit_price=Decimal("500.01"))]
    breakdown = calculate_total(items, "cliente@normal.com")

    assert breakdown.subtotal == Decimal("500.01")
    assert breakdown.volume_discount == Decimal("50.00")
    assert breakdown.total == Decimal("450.01")


def test_cliente_vip_descuento_compuesto():
    """Regla: Cliente VIP (5% adicional sobre monto ya rebajado). Tipo: unitaria.
    Detectaría: calcular el 5% VIP sobre el subtotal original en lugar del monto rebajado.
    """
    # Subtotal 1,000 -> 10% volumen = 100 -> Resta 900 -> 5% VIP sobre 900 = 45 -> Total = 855
    items = [PricedItem(sku="CAC-NIB", quantity=10, unit_price=Decimal("100.00"))]
    breakdown = calculate_total(items, "socio@vip.com")

    assert breakdown.subtotal == Decimal("1000.00")
    assert breakdown.volume_discount == Decimal("100.00")
    assert breakdown.vip_discount == Decimal("45.00")
    assert breakdown.total == Decimal("855.00")


def test_redondeo_medio_centavo_hacia_arriba():
    """Regla: Redondeo: montos calculados con Decimal y medio centavo hacia arriba. Tipo: unitaria.
    Detectaría: usar redondeo par (ROUND_HALF_EVEN), truncamiento o redondeo hacia abajo.
    """
    # 0.005 sube a 0.01; 0.004 baja a 0.00
    assert money(Decimal("10.005")) == Decimal("10.01")
    assert money(Decimal("10.004")) == Decimal("10.00")


def test_edicion_orden_pending_recalcula_todo():
    """Regla: Edición de órdenes: solo en PENDING y recalcula todo. Tipo: integracion.
    Detectaría: actualizar ítems sin recalcular subtotal, descuentos o total de la orden.
    """
    clock = FixedClock(datetime(2026, 10, 15, 10, 0, tzinfo=UTC))
    container = Container(clock=clock)
    with container.session_factory() as session:
        services = container.build(session)
        # 1 tablilla = 85.00 (sin descuento)
        order = services.orders.create_order(
            "cliente@normal.com", [LineIn(sku="CAC-TAB-70", quantity=1)]
        )
        assert order.status == OrderStatus.PENDING
        assert order.total == Decimal("85.00")

        # Editamos a 10 tablillas = 850.00 -> descuento 10% (85.00) -> total = 765.00
        updated = services.orders.update_items(
            order.id, [LineIn(sku="CAC-TAB-70", quantity=10)]
        )
        session.commit()

        assert updated.status == OrderStatus.PENDING
        assert updated.subtotal == Decimal("850.00")
        assert updated.total == Decimal("765.00")


def test_edicion_orden_no_pending_rechaza_409():
    """Regla: Edición de órdenes: solo en PENDING. Tipo: integracion.
    Detectaría: permitir editar pedidos que ya fueron pagados o no lanzar 409 Conflict.
    """
    clock = FixedClock(datetime(2026, 10, 15, 10, 0, tzinfo=UTC))
    container = Container(clock=clock)
    with container.session_factory() as session:
        services = container.build(session)
        order = services.orders.create_order(
            "cliente@normal.com", [LineIn(sku="CAC-TAB-70", quantity=1)]
        )
        services.orders.pay(order.id, order.total)
        session.commit()
        assert order.status == OrderStatus.PAID

        # Intentar editar una orden PAID debe lanzar 409 Conflict
        with pytest.raises(Conflict) as exc_info:
            services.orders.update_items(order.id, [LineIn(sku="CAC-TAB-70", quantity=2)])
        assert exc_info.value.status_code == 409


def test_pago_a_las_24_horas_exactas_se_acepta():
    """Regla: Plazo de pago: a las 24 horas exactas todavía se acepta. Tipo: integracion.
    Detectaría: cambiar > 24h por >= 24h rechazando pagos en el límite exacto.
    """
    inicio = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    clock = FixedClock(inicio)
    container = Container(clock=clock)
    with container.session_factory() as session:
        services = container.build(session)
        order = services.orders.create_order(
            "cliente@normal.com", [LineIn(sku="CAC-TAB-70", quantity=1)]
        )
        session.commit()

        # Avanzar el reloj exactamente 24 horas
        clock.advance(hours=24)

        paid_order = services.orders.pay(order.id, order.total)
        session.commit()
        assert paid_order.status == OrderStatus.PAID


def test_pago_despues_de_24_horas_rechaza_409():
    """Regla: Plazo de pago: pasadas 24 horas se rechaza con 409. Tipo: integracion.
    Detectaría: permitir pagar fuera de plazo o no lanzar 409 Conflict al expirar ventana.
    """
    inicio = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    clock = FixedClock(inicio)
    container = Container(clock=clock)
    with container.session_factory() as session:
        services = container.build(session)
        order = services.orders.create_order(
            "cliente@normal.com", [LineIn(sku="CAC-TAB-70", quantity=1)]
        )
        session.commit()

        # Avanzar el reloj 24 horas y 1 segundo
        clock.advance(hours=24, seconds=1)

        with pytest.raises(Conflict) as exc_info:
            services.orders.pay(order.id, order.total)
        assert exc_info.value.status_code == 409
