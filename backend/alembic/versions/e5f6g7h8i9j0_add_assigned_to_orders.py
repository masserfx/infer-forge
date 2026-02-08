"""add assigned_to to orders

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-02-08 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: str | None = "d4e5f6g7h8i9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_orders_assigned_to", "orders", ["assigned_to"])
    op.create_foreign_key(
        "fk_orders_assigned_to_users",
        "orders",
        "users",
        ["assigned_to"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_orders_assigned_to_users", "orders", type_="foreignkey")
    op.drop_index("ix_orders_assigned_to", table_name="orders")
    op.drop_column("orders", "assigned_to")
