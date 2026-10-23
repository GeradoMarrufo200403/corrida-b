from decimal import Decimal

from pydantic import BaseModel


class ProductOut(BaseModel):
    sku: str
    name: str
    price: Decimal
    perishable: bool
