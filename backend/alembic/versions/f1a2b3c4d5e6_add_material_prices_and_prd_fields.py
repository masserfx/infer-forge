"""add material_prices table and PRD gap fields

Revision ID: f1a2b3c4d5e6
Revises: e6c0d56e02fa
Create Date: 2026-02-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e6c0d56e02fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- material_prices table ---
    op.create_table(
        "material_prices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("specification", sa.String(255), nullable=True),
        sa.Column("material_grade", sa.String(100), nullable=True),
        sa.Column("form", sa.String(100), nullable=True),
        sa.Column("dimension", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="kg"),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("supplier", sa.String(255), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_material_prices_name", "material_prices", ["name"])
    op.create_index("ix_material_prices_material_grade", "material_prices", ["material_grade"])
    op.create_index("ix_material_prices_form", "material_prices", ["form"])
    op.create_index("ix_material_prices_is_active", "material_prices", ["is_active"])
    op.create_index("ix_material_prices_valid_from", "material_prices", ["valid_from"])
    op.create_index("ix_material_prices_valid_to", "material_prices", ["valid_to"])

    # --- customers: add discount/category fields ---
    op.add_column(
        "customers",
        sa.Column(
            "category",
            sa.String(1),
            nullable=True,
            server_default="C",
            comment="A=Klíčový, B=Běžný, C=Nový/jednorázový",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "discount_percent",
            sa.Numeric(5, 2),
            nullable=True,
            server_default="0.00",
            comment="Sazba slevy 0.00-100.00",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "payment_terms_days",
            sa.Integer(),
            nullable=True,
            server_default="14",
            comment="Splatnost faktur ve dnech",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "credit_limit",
            sa.Numeric(12, 2),
            nullable=True,
            comment="Kreditní limit zákazníka",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Interní poznámky ke klientovi",
        ),
    )

    # --- orders: add source_offer_id FK ---
    op.add_column(
        "orders",
        sa.Column(
            "source_offer_id",
            sa.UUID(),
            sa.ForeignKey("offers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_orders_source_offer_id", "orders", ["source_offer_id"])

    # --- offers: add converted_to_order_id FK ---
    op.add_column(
        "offers",
        sa.Column(
            "converted_to_order_id",
            sa.UUID(),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_offers_converted_to_order_id", "offers", ["converted_to_order_id"])

    # --- inbox_messages: add order_id FK and auto_reply_sent ---
    op.add_column(
        "inbox_messages",
        sa.Column(
            "order_id",
            sa.UUID(),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_inbox_messages_order_id", "inbox_messages", ["order_id"])

    op.add_column(
        "inbox_messages",
        sa.Column(
            "auto_reply_sent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    # --- inbox_messages ---
    op.drop_column("inbox_messages", "auto_reply_sent")
    op.drop_index("ix_inbox_messages_order_id", table_name="inbox_messages")
    op.drop_column("inbox_messages", "order_id")

    # --- offers ---
    op.drop_index("ix_offers_converted_to_order_id", table_name="offers")
    op.drop_column("offers", "converted_to_order_id")

    # --- orders ---
    op.drop_index("ix_orders_source_offer_id", table_name="orders")
    op.drop_column("orders", "source_offer_id")

    # --- customers ---
    op.drop_column("customers", "notes")
    op.drop_column("customers", "credit_limit")
    op.drop_column("customers", "payment_terms_days")
    op.drop_column("customers", "discount_percent")
    op.drop_column("customers", "category")

    # --- material_prices ---
    op.drop_index("ix_material_prices_valid_to", table_name="material_prices")
    op.drop_index("ix_material_prices_valid_from", table_name="material_prices")
    op.drop_index("ix_material_prices_is_active", table_name="material_prices")
    op.drop_index("ix_material_prices_form", table_name="material_prices")
    op.drop_index("ix_material_prices_material_grade", table_name="material_prices")
    op.drop_index("ix_material_prices_name", table_name="material_prices")
    op.drop_table("material_prices")
