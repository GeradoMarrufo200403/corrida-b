from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_email: Mapped[str] = mapped_column(String(254), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(
            OrderStatus,
            native_enum=False,
            length=16,
            create_constraint=True,
            name="order_status",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    items: Mapped[list[OrderItem]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by=OrderItem.id
    )
