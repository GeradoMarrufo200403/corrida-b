"""agregar campos de envio a orders

Revision ID: 59138164fa96
Revises: 0001
"""
import sqlalchemy as sa

from alembic import op

revision = '59138164fa96'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("shipping_status", sa.String(32), nullable=True))
    op.add_column("orders", sa.Column("tracking_number", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "tracking_number")
    op.drop_column("orders", "shipping_status")

