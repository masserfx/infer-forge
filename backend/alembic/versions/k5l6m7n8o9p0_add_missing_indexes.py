"""Add missing indexes for audit trail, segmentation, and email lookup.

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-02-10 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "k5l6m7n8o9p0"
down_revision = "j4k5l6m7n8o9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_orders_created_by", "orders", ["created_by"])
    op.create_index("ix_customers_category", "customers", ["category"])
    op.create_index(
        "ix_inbox_messages_from_email_received_at",
        "inbox_messages",
        ["from_email", "received_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_inbox_messages_from_email_received_at", table_name="inbox_messages")
    op.drop_index("ix_customers_category", table_name="customers")
    op.drop_index("ix_orders_created_by", table_name="orders")
