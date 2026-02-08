"""add subcontractors and subcontracts tables

Revision ID: c3d4e5f6g7h8
Revises: f1a2b3c4d5e6
Create Date: 2026-02-08 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- subcontractors table ---
    op.create_table(
        "subcontractors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ico", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("specialization", sa.String(255), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subcontractors_name", "subcontractors", ["name"], unique=False
    )
    op.create_index(
        "ix_subcontractors_is_active", "subcontractors", ["is_active"], unique=False
    )
    op.create_index(
        "ix_subcontractors_specialization",
        "subcontractors",
        ["specialization"],
        unique=False,
    )

    # --- subcontracts table ---
    op.create_table(
        "subcontracts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("subcontractor_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subcontractor_id"], ["subcontractors.id"]
        ),
    )
    op.create_index(
        "ix_subcontracts_order_id", "subcontracts", ["order_id"], unique=False
    )
    op.create_index(
        "ix_subcontracts_subcontractor_id",
        "subcontracts",
        ["subcontractor_id"],
        unique=False,
    )
    op.create_index(
        "ix_subcontracts_status", "subcontracts", ["status"], unique=False
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_subcontracts_status", table_name="subcontracts")
    op.drop_index("ix_subcontracts_subcontractor_id", table_name="subcontracts")
    op.drop_index("ix_subcontracts_order_id", table_name="subcontracts")
    op.drop_index("ix_subcontractors_specialization", table_name="subcontractors")
    op.drop_index("ix_subcontractors_is_active", table_name="subcontractors")
    op.drop_index("ix_subcontractors_name", table_name="subcontractors")

    # Drop tables
    op.drop_table("subcontracts")
    op.drop_table("subcontractors")
