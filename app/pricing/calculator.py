from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.shared.errors import ValidationFailed
from app.shared.schemas import LineIn

VOLUME_THRESHOLD = Decimal(500)
VOLUME_RATE = Decimal("0.10")
VIP_RATE = Decimal("0.05")
VIP_DOMAIN = "@vip.com"
CENTS = Decimal("0.01")


@dataclass
class PricedItem:
    sku: str
    quantity: int
    unit_price: Decimal


@dataclass
class PriceBreakdown:
    subtotal: Decimal
    volume_discount: Decimal
    vip_discount: Decimal
    total: Decimal


def money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def validate_lines(lines: list[LineIn]) -> None:
    if not lines:
        raise ValidationFailed("El pedido debe tener al menos una línea", "empty_order")
    for line in lines:
        if line.quantity <= 0:
            raise ValidationFailed(
                f"La cantidad de {line.sku} debe ser mayor a cero", "invalid_quantity"
            )


def merge_lines(lines: list[LineIn]) -> list[LineIn]:
    merged: dict[str, int] = {}
    for line in lines:
        merged[line.sku] = merged.get(line.sku, 0) + line.quantity
    return [LineIn(sku=sku, quantity=qty) for sku, qty in merged.items()]


def is_vip(customer_email: str) -> bool:
    return customer_email.lower().endswith(VIP_DOMAIN)


def calculate_total(items: list[PricedItem], customer_email: str) -> PriceBreakdown:
    subtotal = money(sum((i.unit_price * i.quantity for i in items), Decimal(0)))
    volume_discount = Decimal("0.00")
    if subtotal > VOLUME_THRESHOLD:
        volume_discount = money(subtotal * VOLUME_RATE)
    after_volume = subtotal - volume_discount
    vip_discount = Decimal("0.00")
    if is_vip(customer_email):
        vip_discount = money(after_volume * VIP_RATE)
    total = money(after_volume - vip_discount)
    return PriceBreakdown(subtotal, volume_discount, vip_discount, total)
