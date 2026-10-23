from sqlalchemy import select
from sqlalchemy.orm import Session

from app.inventory.models import Lot, Product, Reservation


class InventoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_product(self, product: Product) -> None:
        self.session.add(product)

    def add_lot(self, lot: Lot) -> None:
        self.session.add(lot)

    def get_product(self, sku: str) -> Product | None:
        return self.session.get(Product, sku)

    def list_products(self) -> list[Product]:
        return list(self.session.scalars(select(Product).order_by(Product.sku)))

    def get_lot(self, code: str) -> Lot:
        return self.session.get_one(Lot, code)

    def lots_for(self, sku: str, lock: bool = False) -> list[Lot]:
        """Lotes de un SKU ordenados por caducidad. lock=True los bloquea (FOR UPDATE)
        para que dos reservas simultáneas no vendan el mismo stock."""
        stmt = select(Lot).where(Lot.sku == sku).order_by(Lot.expires_on, Lot.code)
        if lock:
            stmt = stmt.with_for_update()
        return list(self.session.scalars(stmt))

    def get_reservation(self, order_id: int) -> Reservation | None:
        return self.session.get(Reservation, order_id)

    def save_reservation(self, reservation: Reservation) -> None:
        self.session.add(reservation)
        self.session.flush()
