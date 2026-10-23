"""Esquema inicial de OrderFlow: productos, lotes, ordenes y reservas.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("sku", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("perishable", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "lots",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("sku", sa.String(32), sa.ForeignKey("products.sku"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("expires_on", sa.Date, nullable=False),
        sa.Column("reserved", sa.Integer, nullable=False, server_default="0"),
        sa.CheckConstraint("quantity >= 0", name="ck_lots_quantity_non_negative"),
        sa.CheckConstraint("reserved >= 0 AND reserved <= quantity", name="ck_lots_reserved_in_range"),
    )
    op.create_index("ix_lots_sku", "lots", ["sku"])
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, sa.Identity(always=False), primary_key=True),
        sa.Column("customer_email", sa.String(254), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("shipped_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PAID', 'SHIPPED', 'CANCELLED')", name="order_status"
        ),
    )
    op.create_index("ix_orders_customer_email", "orders", ["customer_email"])
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer, sa.Identity(always=False), primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(32), sa.ForeignKey("products.sku"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_table(
        "reservations",
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
    )
    op.create_table(
        "reservation_allocations",
        sa.Column("id", sa.Integer, sa.Identity(always=False), primary_key=True),
        sa.Column(
            "order_id", sa.Integer, sa.ForeignKey("reservations.order_id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("lot_code", sa.String(32), sa.ForeignKey("lots.code"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_allocations_quantity_positive"),
    )
    op.create_index("ix_reservation_allocations_order_id", "reservation_allocations", ["order_id"])


def downgrade() -> None:
    op.drop_table("reservation_allocations")
    op.drop_table("reservations")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("lots")
    op.drop_table("products")
