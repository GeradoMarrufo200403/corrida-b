from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orders.models import Order


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, order: Order) -> None:
        """Inserta la orden y obtiene su id de la secuencia de Postgres."""
        self.session.add(order)
        self.session.flush()

    def get(self, order_id: int, lock: bool = False) -> Order | None:
        """lock=True toma un bloqueo de fila (SELECT ... FOR UPDATE) hasta el fin de la transacción."""
        stmt = select(Order).where(Order.id == order_id)
        if lock:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).one_or_none()

    def list(self) -> list[Order]:
        return list(self.session.scalars(select(Order).order_by(Order.id)))
