"""add notifications and order_embeddings tables

Revision ID: a1b2c3d4e5f6
Revises: dde641b78bb9
Create Date: 2026-02-08 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "dde641b78bb9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add notifications and order_embeddings tables."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- notifications table ---
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Enum(
                "email_new",
                "email_classified",
                "pohoda_sync_complete",
                "calculation_complete",
                "order_status_changed",
                "document_uploaded",
                name="notificationtype",
                native_enum=False,
                length=50,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=512), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_read", "notifications", ["read"])

    # --- order_embeddings table ---
    op.create_table(
        "order_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "order_id",
            sa.Uuid(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_embeddings")),
        sa.UniqueConstraint("order_id", name=op.f("uq_order_embeddings_order_id")),
    )
    op.create_index(
        op.f("ix_order_embeddings_order_embeddings_order_id"),
        "order_embeddings",
        ["order_id"],
    )

    # Add vector column using raw SQL (pgvector)
    op.execute(
        "ALTER TABLE order_embeddings ADD COLUMN embedding vector(384) NOT NULL"
    )

    # Create IVFFlat index for vector similarity search
    # Note: IVFFlat needs training data, so for small datasets use HNSW instead
    op.execute(
        "CREATE INDEX ix_order_embeddings_embedding_hnsw "
        "ON order_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Remove notifications and order_embeddings tables."""
    op.drop_table("order_embeddings")
    op.drop_table("notifications")
    # Don't drop vector extension as other tables might use it
