"""Change customer FK from CASCADE to RESTRICT for ISO 9001 compliance.

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-02-10 06:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "i3j4k5l6m7n8"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old CASCADE FK and create RESTRICT FK on orders.customer_id
    op.drop_constraint("orders_customer_id_fkey", "orders", type_="foreignkey")
    op.create_foreign_key(
        "orders_customer_id_fkey",
        "orders",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("orders_customer_id_fkey", "orders", type_="foreignkey")
    op.create_foreign_key(
        "orders_customer_id_fkey",
        "orders",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="CASCADE",
    )
