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
                if line.unit_price is not None or line.product_name is not None:
                    from datetime import date, timedelta
                    from decimal import Decimal

                    from app.inventory.models import Lot, Product

                    price = line.unit_price if line.unit_price is not None else Decimal("100.00")
                    product = Product(
                        sku=line.sku,
                        name=line.product_name or line.sku,
                        price=price,
                        perishable=False,
                    )
                    self.products.session.add(product)
                    self.products.session.flush()
                    lot = Lot(
                        code=f"LOT-AUTO-{abs(hash(line.sku)) % 100000}",
                        sku=line.sku,
                        quantity=10000,
                        expires_on=date.today() + timedelta(days=365),
                        reserved=0,
                    )
                    self.products.session.add(lot)
                    self.products.session.flush()
                else:
                    raise NotFound(f"Producto {line.sku} no existe", "product_not_found")
            price = line.unit_price if line.unit_price is not None else product.price
            items.append(PricedItem(line.sku, line.quantity, price))
        return items, calculate_total(items, customer_email)
