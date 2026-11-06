from decimal import Decimal

from pydantic import BaseModel, model_validator


class LineIn(BaseModel):
    sku: str | None = None
    product_name: str | None = None
    quantity: int = 1
    unit_price: Decimal | None = None

    @model_validator(mode="after")
    def populate_sku(self):
        if not self.sku:
            self.sku = self.product_name or "ITEM-DEFAULT"
        return self
