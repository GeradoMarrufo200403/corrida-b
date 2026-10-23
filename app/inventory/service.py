from app.inventory.models import Reservation, ReservationAllocation
from app.inventory.repository import InventoryRepository
from app.shared.clock import Clock
from app.shared.errors import Conflict, NotFound
from app.shared.schemas import LineIn


class InventoryService:
    def __init__(self, repo: InventoryRepository, clock: Clock):
        self.repo = repo
        self.clock = clock

    def stock_of(self, sku: str) -> dict:
        if self.repo.get_product(sku) is None:
            raise NotFound(f"Producto {sku} no existe", "product_not_found")
        today = self.clock.today()
        lots = sorted(self.repo.lots_for(sku), key=lambda lot: lot.expires_on)
        usable = [lot for lot in lots if lot.expires_on >= today]
        return {
            "sku": sku,
            "available": sum(lot.quantity - lot.reserved for lot in usable),
            "lots": [
                {
                    "code": lot.code,
                    "quantity": lot.quantity,
                    "reserved": lot.reserved,
                    "expires_on": lot.expires_on.isoformat(),
                    "expired": lot.expires_on < today,
                }
                for lot in lots
            ],
        }

    def reserve(self, order_id: int, lines: list[LineIn]) -> Reservation:
        """Reserva FEFO (primero en caducar, primero en salir). Todo o nada.
        Si la orden ya tenía una reserva activa, se reemplaza solo si la nueva tiene éxito."""
        today = self.clock.today()
        existing = self.repo.get_reservation(order_id)
        own: dict[str, int] = {}
        if existing and existing.status == "RESERVED":
            own = {a.lot_code: a.quantity for a in existing.allocations}

        for line in lines:
            if self.repo.get_product(line.sku) is None:
                raise NotFound(f"Producto {line.sku} no existe", "product_not_found")
        # Bloqueo de filas (FOR UPDATE) en orden de SKU: evita sobreventa y bloqueos mutuos entre reservas simultáneas.
        locked = {sku: self.repo.lots_for(sku, lock=True) for sku in sorted({l.sku for l in lines})}

        taken: dict[str, int] = {}
        allocations: list[tuple[str, int]] = []
        for line in lines:
            needed = line.quantity
            lots = locked[line.sku]
            for lot in lots:
                if lot.expires_on < today:
                    continue
                free = lot.quantity - lot.reserved + own.get(lot.code, 0) - taken.get(lot.code, 0)
                if free <= 0:
                    continue
                grab = min(free, needed)
                taken[lot.code] = taken.get(lot.code, 0) + grab
                allocations.append((lot.code, grab))
                needed -= grab
                if needed == 0:
                    break
            if needed > 0:
                raise Conflict(f"Stock insuficiente de {line.sku}", "insufficient_stock")

        self._free_reserved(existing)
        for code, qty in allocations:
            self.repo.get_lot(code).reserved += qty
        reservation = existing or Reservation(order_id=order_id)
        reservation.allocations = [
            ReservationAllocation(lot_code=code, quantity=qty) for code, qty in allocations
        ]
        reservation.status = "RESERVED"
        self.repo.save_reservation(reservation)
        return reservation

    def confirm(self, order_id: int) -> None:
        reservation = self.repo.get_reservation(order_id)
        if reservation is None or reservation.status != "RESERVED":
            raise Conflict("La orden no tiene reserva activa", "no_active_reservation")
        for allocation in reservation.allocations:
            lot = self.repo.get_lot(allocation.lot_code)
            lot.reserved -= allocation.quantity
            lot.quantity -= allocation.quantity
        reservation.status = "CONFIRMED"

    def release(self, order_id: int) -> None:
        reservation = self.repo.get_reservation(order_id)
        self._free_reserved(reservation)

    def _free_reserved(self, reservation: Reservation | None) -> None:
        if reservation is None or reservation.status != "RESERVED":
            return
        for allocation in reservation.allocations:
            self.repo.get_lot(allocation.lot_code).reserved -= allocation.quantity
        reservation.status = "RELEASED"
