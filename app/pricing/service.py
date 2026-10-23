from app.inventory.repository import InventoryRepository
from app.pricing.calculator import (
    PriceBreakdown,
    PricedItem,
    calculate_total,
    merge_lines,
    validate_lines,
)
from app.shared.errors import NotFound
from app.shared.schemas import LineIn


class PricingService:
    def __init__(self, products: InventoryRepository):
        self.products = products

    def quote(
        self, lines: list[LineIn], customer_email: str
    ) -> tuple[list[PricedItem], PriceBreakdown]:
        validate_lines(lines)
        items = []
        for line in merge_lines(lines):
            product = self.products.get_product(line.sku)
            if product is None:
                raise NotFound(f"Producto {line.sku} no existe", "product_not_found")
            items.append(PricedItem(line.sku, line.quantity, product.price))
        return items, calculate_total(items, customer_email)
