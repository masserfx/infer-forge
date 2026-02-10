"""Add CHECK constraints on discount_percent and margin_percent.

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-02-10 08:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "j4k5l6m7n8o9"
down_revision = "i3j4k5l6m7n8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_customers_discount_percent_range",
        "customers",
        "discount_percent >= 0 AND discount_percent <= 100",
    )
    op.create_check_constraint(
        "ck_calculations_margin_percent_range",
        "calculations",
        "margin_percent >= 0 AND margin_percent <= 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_calculations_margin_percent_range", "calculations", type_="check")
    op.drop_constraint("ck_customers_discount_percent_range", "customers", type_="check")
