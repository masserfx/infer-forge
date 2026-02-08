"""add operations table

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-02-08 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create operations table
    op.create_table(
        "operations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "order_id",
            sa.UUID(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("duration_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("responsible", sa.String(255), nullable=True),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_operations_order_id", "operations", ["order_id"])
    op.create_index("ix_operations_status", "operations", ["status"])
    op.create_index(
        "ix_operations_order_id_sequence",
        "operations",
        ["order_id", "sequence"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_operations_order_id_sequence", table_name="operations")
    op.drop_index("ix_operations_status", table_name="operations")
    op.drop_index("ix_operations_order_id", table_name="operations")

    # Drop table
    op.drop_table("operations")
