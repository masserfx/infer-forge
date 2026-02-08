"""Material price model for cost database."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPKMixin


class MaterialPrice(UUIDPKMixin, TimestampMixin, Base):
    """Material price entry for cost estimation.

    Stores unit prices for steel materials, fittings, and other fabrication components.
    Supports validity periods and supplier tracking for accurate cost calculations.

    Attributes:
        name: Material name (e.g., "Ocel S235JR").
        specification: Technical specification (e.g., "EN 10025-2, tloušťka 10mm").
        material_grade: Material grade/standard (e.g., "S235JR", "P265GH", "1.4301").
        form: Material form (e.g., "plech", "trubka", "tyč", "profil").
        dimension: Dimension specification (e.g., "DN100", "10x1000x2000mm").
        unit: Measurement unit (e.g., "kg", "m", "m2", "ks").
        unit_price: Price per unit in CZK.
        supplier: Supplier name (e.g., "Ferona", "ArcelorMittal").
        valid_from: Start date of price validity.
        valid_to: End date of price validity (NULL = indefinite).
        is_active: Whether price is currently active.
        notes: Additional notes or remarks.
    """

    __tablename__ = "material_prices"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    specification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material_grade: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    form: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    dimension: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_material_prices_valid_from", "valid_from"),
        Index("ix_material_prices_valid_to", "valid_to"),
    )

    def __repr__(self) -> str:
        return (
            f"<MaterialPrice(id={self.id}, name='{self.name}', "
            f"grade='{self.material_grade}', price={self.unit_price} {self.unit})>"
        )
