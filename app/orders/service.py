from datetime import timedelta
from decimal import Decimal

from app.inventory.service import InventoryService
from app.notifications import NotificationSender
from app.orders.models import Order, OrderItem, OrderStatus
from app.orders.repository import OrderRepository
from app.orders.states import TRANSITIONS
from app.pricing.service import PricingService
from app.shared.clock import Clock
from app.shared.errors import Conflict, NotFound, ValidationFailed
from app.shared.schemas import LineIn

PAYMENT_WINDOW = timedelta(hours=24)


class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        pricing: PricingService,
        inventory: InventoryService,
        notifier: NotificationSender,
        clock: Clock,
    ):
        self.repo = repo
        self.pricing = pricing
        self.inventory = inventory
        self.notifier = notifier
        self.clock = clock

    @staticmethod
    def _to_items(priced) -> list[OrderItem]:
        return [OrderItem(sku=i.sku, quantity=i.quantity, unit_price=i.unit_price) for i in priced]

    def create_order(self, customer_email: str, lines: list[LineIn]) -> Order:
        if "@" not in customer_email:
            raise ValidationFailed("Correo del cliente inválido", "invalid_email")
        items, breakdown = self.pricing.quote(lines, customer_email)
        order = Order(
            customer_email=customer_email,
            items=self._to_items(items),
            status=OrderStatus.PENDING,
            subtotal=breakdown.subtotal,
            total=breakdown.total,
            created_at=self.clock.now(),
        )
        self.repo.add(order)  # obtiene el id de la secuencia de Postgres
        self.inventory.reserve(order.id, [LineIn(sku=i.sku, quantity=i.quantity) for i in items])
        return order

    def get_order(self, order_id: int, lock: bool = False) -> Order:
        order = self.repo.get(order_id, lock=lock)
        if order is None:
            raise NotFound(f"Orden {order_id} no existe", "order_not_found")
        return order

    def list_orders(self) -> list[Order]:
        return self.repo.list()

    def update_items(self, order_id: int, lines: list[LineIn]) -> Order:
        order = self.get_order(order_id, lock=True)
        if order.status != OrderStatus.PENDING:
            raise Conflict("Solo se pueden editar órdenes PENDING", "order_not_editable")
        items, breakdown = self.pricing.quote(lines, order.customer_email)
        self.inventory.reserve(order.id, [LineIn(sku=i.sku, quantity=i.quantity) for i in items])
        order.items = self._to_items(items)
        order.subtotal = breakdown.subtotal
        order.total = breakdown.total
        return order

    def pay(self, order_id: int, amount: Decimal) -> Order:
        order = self.get_order(order_id, lock=True)
        self._apply_transition(order, OrderStatus.PAID)
        if self.clock.now() - order.created_at > PAYMENT_WINDOW:
            raise Conflict("La ventana de pago de 24 horas expiró", "payment_window_expired")
        if amount != order.total:
            raise ValidationFailed("El monto debe ser exactamente el total", "payment_mismatch")
        order.status = OrderStatus.PAID
        order.paid_at = self.clock.now()
        self.notifier.send(order.customer_email, f"Recibimos el pago de tu orden {order.id}")
        return order

    def ship(self, order_id: int) -> Order:
        order = self.get_order(order_id, lock=True)
        self._apply_transition(order, OrderStatus.SHIPPED)
        self.inventory.confirm(order.id)
        order.status = OrderStatus.SHIPPED
        order.shipped_at = self.clock.now()
        self.notifier.send(order.customer_email, f"Tu orden {order.id} va en camino")
        return order

    def cancel(self, order_id: int) -> Order:
        from app.pricing.calculator import money

        order = self.get_order(order_id, lock=True)
        self._apply_transition(order, OrderStatus.CANCELLED)

        refund_amount = Decimal("0.00")
        penalty = Decimal("0.00")

        if order.status == OrderStatus.PAID:
            if order.paid_at and (self.clock.now() - order.paid_at > timedelta(hours=24)):
                penalty = money(order.total * Decimal("0.10"))
                refund_amount = order.total - penalty
            else:
                refund_amount = order.total
                penalty = Decimal("0.00")

        order.status = OrderStatus.CANCELLED
        self.inventory.release(order.id)

        order.refund_amount = refund_amount
        order.penalty = penalty
        return order

    def _apply_transition(self, order: Order, target: OrderStatus) -> None:
        if target not in TRANSITIONS[order.status]:
            raise Conflict(
                f"No se puede pasar de {order.status.value} a {target.value}",
                "invalid_transition",
            )
