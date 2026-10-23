from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.container import Container
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


def test_edicion_no_reinicia_plazo_de_pago_de_24h():
    """Regla: ORD-05 Plazo de pago: editar la orden no reinicia el plazo de 24 horas. Tipo: integracion.

    Detectaría: sabotaje M4 (reiniciar created_at en update_items permitiendo pagar después de 24h de creación).
    """
    inicio = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    clock = FixedClock(inicio)
    container = Container(clock=clock)

    with container.session_factory() as session:
        services = container.build(session)
        # 1. Crear orden en T0
        order = services.orders.create_order(
            "cliente@normal.com", [LineIn(sku="CAC-TAB-70", quantity=1)]
        )
        session.commit()

        # 2. Editar la orden a las 20 horas de creada (dentro del plazo)
        clock.advance(hours=20)
        services.orders.update_items(order.id, [LineIn(sku="CAC-TAB-70", quantity=2)])
        session.commit()

        # 3. Avanzar el reloj 5 horas más (han pasado 25 horas desde la creación)
        # Bajo la regla ORD-05, pasaron 25 horas desde T0 y debe rechazar con 409 Conflict.
        # Con el sabotaje M4, solo pasaron 5 horas desde la edición y el pago pasaría indebidamente.
        clock.advance(hours=5)

        with pytest.raises(Conflict) as exc_info:
            services.orders.pay(order.id, order.total)
        assert exc_info.value.status_code == 409
