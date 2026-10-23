from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.db import make_engine
from app.inventory.repository import InventoryRepository
from app.inventory.service import InventoryService
from app.notifications import ConsoleNotificationSender, NotificationSender
from app.orders.repository import OrderRepository
from app.orders.service import OrderService
from app.pricing.service import PricingService
from app.shared.clock import Clock, SystemClock


@dataclass
class Services:
    """Servicios ligados a UNA sesión de base de datos (una transacción por petición)."""

    inventory_repo: InventoryRepository
    inventory: InventoryService
    pricing: PricingService
    orders: OrderService


class Container:
    """Ensambla las dependencias. Los tests pueden inyectar un reloj, un notificador falso y otra URL."""

    def __init__(
        self,
        clock: Clock | None = None,
        notifier: NotificationSender | None = None,
        database_url: str | None = None,
    ):
        self.clock = clock or SystemClock()
        self.notifier = notifier or ConsoleNotificationSender()
        self.engine = make_engine(database_url)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def build(self, session: Session) -> Services:
        inventory_repo = InventoryRepository(session)
        inventory = InventoryService(inventory_repo, self.clock)
        pricing = PricingService(inventory_repo)
        orders = OrderService(OrderRepository(session), pricing, inventory, self.notifier, self.clock)
        return Services(inventory_repo, inventory, pricing, orders)
