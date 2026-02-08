"""Material price business logic service."""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog, MaterialPrice
from app.schemas import (
    MaterialPriceCreate,
    MaterialPriceImportResult,
    MaterialPriceUpdate,
)

logger = logging.getLogger(__name__)


class MaterialPriceService:
    """Service for managing material prices."""

    def __init__(self, db: AsyncSession, user_id: UUID | None = None):
        self.db = db
        self.user_id = user_id

    async def _create_audit_log(
        self,
        action: AuditAction,
        entity_id: UUID,
        changes: dict[str, object] | None = None,
    ) -> None:
        """Create audit log entry."""
        audit = AuditLog(
            user_id=self.user_id,
            action=action,
            entity_type="material_price",
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        material_grade: str | None = None,
        form: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[MaterialPrice], int]:
        """Get all material prices with optional filters.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            search: Search string for name or specification.
            material_grade: Filter by material grade.
            form: Filter by material form.
            is_active: Filter by active status.

        Returns:
            Tuple of (list of MaterialPrice, total count).
        """
        query = select(MaterialPrice)
        count_query = select(func.count()).select_from(MaterialPrice)

        # Apply filters
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    MaterialPrice.name.ilike(search_pattern),
                    MaterialPrice.specification.ilike(search_pattern),
                )
            )
            count_query = count_query.where(
                or_(
                    MaterialPrice.name.ilike(search_pattern),
                    MaterialPrice.specification.ilike(search_pattern),
                )
            )

        if material_grade:
            query = query.where(MaterialPrice.material_grade == material_grade)
            count_query = count_query.where(MaterialPrice.material_grade == material_grade)

        if form:
            query = query.where(MaterialPrice.form == form)
            count_query = count_query.where(MaterialPrice.form == form)

        if is_active is not None:
            query = query.where(MaterialPrice.is_active == is_active)
            count_query = count_query.where(MaterialPrice.is_active == is_active)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.order_by(MaterialPrice.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id(self, price_id: UUID) -> MaterialPrice | None:
        """Get material price by ID."""
        result = await self.db.execute(
            select(MaterialPrice).where(MaterialPrice.id == price_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: MaterialPriceCreate) -> MaterialPrice:
        """Create a new material price."""
        price = MaterialPrice(
            name=data.name,
            specification=data.specification,
            material_grade=data.material_grade,
            form=data.form,
            dimension=data.dimension,
            unit=data.unit,
            unit_price=data.unit_price,
            supplier=data.supplier,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
            is_active=data.is_active,
            notes=data.notes,
        )
        self.db.add(price)
        await self.db.flush()
        await self.db.refresh(price)

        # Audit trail
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_id=price.id,
            changes={
                "name": data.name,
                "material_grade": data.material_grade,
                "unit_price": str(data.unit_price),
                "unit": data.unit,
                "supplier": data.supplier,
            },
        )

        logger.info(
            "material_price_created id=%s name=%s price=%s",
            price.id,
            data.name,
            data.unit_price,
        )

        return price

    async def update(
        self,
        price_id: UUID,
        data: MaterialPriceUpdate,
    ) -> MaterialPrice | None:
        """Update an existing material price."""
        price = await self.get_by_id(price_id)
        if not price:
            return None

        changes: dict[str, object] = {}
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            old_value = getattr(price, field)
            if old_value != value:
                changes[field] = {"old": str(old_value), "new": str(value)}
                setattr(price, field, value)

        if changes:
            await self.db.flush()
            await self.db.refresh(price)

            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_id=price.id,
                changes=changes,
            )

            logger.info("material_price_updated id=%s changes=%s", price_id, changes)

        return price

    async def delete(self, price_id: UUID) -> bool:
        """Delete a material price."""
        price = await self.get_by_id(price_id)
        if not price:
            return False

        await self._create_audit_log(
            action=AuditAction.DELETE,
            entity_id=price.id,
            changes={
                "deleted_name": price.name,
                "material_grade": price.material_grade,
                "unit_price": str(price.unit_price),
            },
        )

        await self.db.delete(price)
        await self.db.flush()

        logger.info("material_price_deleted id=%s name=%s", price_id, price.name)

        return True

    async def find_best_price(
        self,
        material_name: str | None = None,
        material_grade: str | None = None,
        dimension: str | None = None,
    ) -> MaterialPrice | None:
        """Find the best (cheapest valid) price for a material.

        Search priority:
        1. Exact material_grade match
        2. Name LIKE match
        3. Cheapest valid price among matches

        Args:
            material_name: Material name to search for.
            material_grade: Material grade (e.g., "S235JR").
            dimension: Dimension specification.

        Returns:
            MaterialPrice or None if no match found.
        """
        today = date.today()
        query = select(MaterialPrice).where(
            MaterialPrice.is_active == True,  # noqa: E712
            MaterialPrice.valid_from <= today,
            or_(
                MaterialPrice.valid_to.is_(None),
                MaterialPrice.valid_to >= today,
            ),
        )

        # Priority 1: Exact material_grade match
        if material_grade:
            grade_query = query.where(MaterialPrice.material_grade == material_grade)
            result = await self.db.execute(
                grade_query.order_by(MaterialPrice.unit_price.asc()).limit(1)
            )
            match = result.scalar_one_or_none()
            if match:
                logger.info(
                    "best_price_found strategy=exact_grade grade=%s price=%s",
                    material_grade,
                    match.unit_price,
                )
                return match

        # Priority 2: Name LIKE match
        if material_name:
            name_pattern = f"%{material_name}%"
            name_query = query.where(MaterialPrice.name.ilike(name_pattern))
            result = await self.db.execute(
                name_query.order_by(MaterialPrice.unit_price.asc()).limit(1)
            )
            match = result.scalar_one_or_none()
            if match:
                logger.info(
                    "best_price_found strategy=name_like name=%s price=%s",
                    material_name,
                    match.unit_price,
                )
                return match

        # No match found
        logger.info(
            "best_price_not_found grade=%s name=%s",
            material_grade,
            material_name,
        )
        return None

    async def import_from_excel(self, file_content: bytes) -> MaterialPriceImportResult:
        """Import material prices from Excel file.

        Expected columns: name, specification, material_grade, form, dimension,
                         unit, unit_price, supplier, valid_from, valid_to, is_active, notes

        Args:
            file_content: Excel file content as bytes.

        Returns:
            MaterialPriceImportResult with success count and errors.
        """
        from app.integrations.excel.parser import ExcelParser

        parser = ExcelParser()
        imported_count = 0
        failed_count = 0
        errors: list[str] = []

        try:
            # Save to temporary file
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name

            # Parse Excel
            rows = await parser.parse_generic(tmp_path)

            for idx, row in enumerate(rows, start=2):  # Start at 2 (1 is header)
                try:
                    # Map Excel columns to MaterialPriceCreate
                    price_data = MaterialPriceCreate(
                        name=str(row.get("name", row.get("název", ""))).strip(),
                        specification=str(row.get("specification", row.get("specifikace", "")))
                        .strip()
                        or None,
                        material_grade=str(
                            row.get("material_grade", row.get("třída_materiálu", ""))
                        ).strip()
                        or None,
                        form=str(row.get("form", row.get("forma", ""))).strip() or None,
                        dimension=str(row.get("dimension", row.get("rozměry", ""))).strip()
                        or None,
                        unit=str(row.get("unit", row.get("jednotka", "kg"))).strip(),
                        unit_price=float(row.get("unit_price", row.get("jednotková_cena", 0))),
                        supplier=str(row.get("supplier", row.get("dodavatel", ""))).strip()
                        or None,
                        valid_from=row.get("valid_from", row.get("platnost_od", date.today())),
                        valid_to=row.get("valid_to", row.get("platnost_do")),
                        is_active=bool(row.get("is_active", row.get("aktivní", True))),
                        notes=str(row.get("notes", row.get("poznámky", ""))).strip() or None,
                    )

                    await self.create(price_data)
                    imported_count += 1

                except Exception as e:
                    failed_count += 1
                    errors.append(f"Řádek {idx}: {str(e)}")
                    logger.warning("import_row_failed row=%s error=%s", idx, str(e))

            # Cleanup
            import os

            os.unlink(tmp_path)

        except Exception as e:
            logger.exception("import_failed error=%s", str(e))
            return MaterialPriceImportResult(
                success=False,
                imported_count=0,
                failed_count=0,
                errors=[f"Import selhal: {str(e)}"],
            )

        logger.info(
            "import_completed imported=%s failed=%s",
            imported_count,
            failed_count,
        )

        return MaterialPriceImportResult(
            success=failed_count == 0,
            imported_count=imported_count,
            failed_count=failed_count,
            errors=errors,
        )
