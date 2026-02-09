"""add direction column to inbox_messages and backfill thread_id on root emails

Revision ID: g1h2i3j4k5l6
Revises: ('e5f6g7h8i9j0', 'f1a2b3c4d5e6')
Create Date: 2026-02-09 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: tuple[str, ...] = ("e5f6g7h8i9j0", "f1a2b3c4d5e6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add direction column with default 'inbound'
    op.add_column(
        "inbox_messages",
        sa.Column(
            "direction",
            sa.String(length=10),
            nullable=False,
            server_default="inbound",
        ),
    )

    # Backfill thread_id on root emails (no references_header = root of thread)
    op.execute(
        "UPDATE inbox_messages SET thread_id = message_id "
        "WHERE thread_id IS NULL AND (references_header IS NULL OR references_header = '')"
    )


def downgrade() -> None:
    op.drop_column("inbox_messages", "direction")
