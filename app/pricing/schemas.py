from decimal import Decimal

from pydantic import BaseModel

from app.shared.schemas import LineIn


class QuoteIn(BaseModel):
    customer_email: str
    items: list[LineIn]


class QuoteOut(BaseModel):
    subtotal: Decimal
    volume_discount: Decimal
    vip_discount: Decimal
    total: Decimal
