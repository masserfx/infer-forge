"""add approval workflow status values to calculations

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-02-09 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h2i3j4k5l6m7"
down_revision: str = "g1h2i3j4k5l6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CalculationStatus uses native_enum=False (VARCHAR column), so no DDL
    # needed for new enum values (pending_approval, rejected).
    # The column length is being extended from 20 to 30 in the model.
    # Alter the column to accommodate the longer values.
    op.alter_column(
        "calculations",
        "status",
        type_=sa.String(30),
        existing_type=sa.String(20),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Revert any pending_approval/rejected back to draft
    op.execute(
        "UPDATE calculations SET status = 'draft' "
        "WHERE status IN ('pending_approval', 'rejected')"
    )
    op.alter_column(
        "calculations",
        "status",
        type_=sa.String(20),
        existing_type=sa.String(30),
        existing_nullable=False,
    )
