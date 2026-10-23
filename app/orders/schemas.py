from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.shared.schemas import LineIn


class OrderCreate(BaseModel):
    customer_email: str
    items: list[LineIn]


class ItemsUpdate(BaseModel):
    items: list[LineIn]


class PaymentIn(BaseModel):
    amount: Decimal


class ItemOut(BaseModel):
    sku: str
    quantity: int
    unit_price: Decimal


class OrderOut(BaseModel):
    id: int
    customer_email: str
    status: str
    items: list[ItemOut]
    subtotal: Decimal
    total: Decimal
    created_at: datetime
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    refund_amount: Decimal | None = None
    penalty: Decimal | None = None
