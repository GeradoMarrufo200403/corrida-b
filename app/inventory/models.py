from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    perishable: Mapped[bool] = mapped_column(Boolean, default=False)


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_lots_quantity_non_negative"),
        CheckConstraint("reserved >= 0 AND reserved <= quantity", name="ck_lots_reserved_in_range"),
    )

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    expires_on: Mapped[date] = mapped_column(Date)
    reserved: Mapped[int] = mapped_column(Integer, default=0)


class ReservationAllocation(Base):
    __tablename__ = "reservation_allocations"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_allocations_quantity_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.order_id", ondelete="CASCADE"), index=True
    )
    lot_code: Mapped[str] = mapped_column(ForeignKey("lots.code"))
    quantity: Mapped[int] = mapped_column(Integer)


class Reservation(Base):
    __tablename__ = "reservations"

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), default="RESERVED")  # RESERVED, CONFIRMED, RELEASED
    allocations: Mapped[list[ReservationAllocation]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by=ReservationAllocation.id
    )
