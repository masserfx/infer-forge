"""Subcontractor and Subcontract business logic service."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog, Subcontract, Subcontractor
from app.schemas.subcontractor import (
    SubcontractCreate,
    SubcontractUpdate,
    SubcontractorCreate,
    SubcontractorUpdate,
)


class SubcontractorService:
    """Service for managing subcontractors and subcontracts with audit trail."""

    def __init__(self, db: AsyncSession, user_id: UUID | None = None):
        """Initialize service.

        Args:
            db: Async database session
            user_id: ID of user performing the operation (for audit trail)
        """
        self.db = db
        self.user_id = user_id

    async def _create_audit_log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID,
        changes: dict[str, object] | None = None,
    ) -> None:
        """Create audit log entry.

        Args:
            action: Audit action type
            entity_type: Type of entity (subcontractor or subcontract)
            entity_id: ID of affected entity
            changes: Dictionary of changes made
        """
        audit = AuditLog(
            user_id=self.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit)

    # --- Subcontractor methods ---

    async def create_subcontractor(
        self, subcontractor_data: SubcontractorCreate
    ) -> Subcontractor:
        """Create a new subcontractor.

        Args:
            subcontractor_data: Subcontractor creation data

        Returns:
            Created subcontractor instance
        """
        subcontractor = Subcontractor(**subcontractor_data.model_dump())
        self.db.add(subcontractor)
        await self.db.flush()
        await self.db.refresh(subcontractor)

        # Audit trail
        changes_dict = subcontractor_data.model_dump()
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_type="subcontractor",
            entity_id=subcontractor.id,
            changes={"created": changes_dict},
        )

        return subcontractor

    async def get_subcontractor_by_id(
        self, subcontractor_id: UUID
    ) -> Subcontractor | None:
        """Get subcontractor by ID.

        Args:
            subcontractor_id: Subcontractor UUID

        Returns:
            Subcontractor instance or None if not found
        """
        result = await self.db.execute(
            select(Subcontractor).where(Subcontractor.id == subcontractor_id)
        )
        return result.scalar_one_or_none()

    async def get_all_subcontractors(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        specialization: str | None = None,
    ) -> tuple[list[Subcontractor], int]:
        """Get all subcontractors with pagination and filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            specialization: Filter by specialization

        Returns:
            Tuple of (list of subcontractor instances, total count)
        """
        query = select(Subcontractor)

        if is_active is not None:
            query = query.where(Subcontractor.is_active == is_active)

        if specialization:
            query = query.where(Subcontractor.specialization.ilike(f"%{specialization}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.order_by(Subcontractor.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        subcontractors = list(result.scalars().all())

        return subcontractors, total

    async def update_subcontractor(
        self,
        subcontractor_id: UUID,
        subcontractor_data: SubcontractorUpdate,
    ) -> Subcontractor | None:
        """Update subcontractor.

        Args:
            subcontractor_id: Subcontractor UUID
            subcontractor_data: Subcontractor update data

        Returns:
            Updated subcontractor instance or None if not found
        """
        subcontractor = await self.get_subcontractor_by_id(subcontractor_id)
        if not subcontractor:
            return None

        # Track changes for audit
        changes: dict[str, object] = {}
        update_data = subcontractor_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            old_value = getattr(subcontractor, field)
            if old_value != value:
                old_str = str(old_value) if isinstance(old_value, Decimal) else old_value
                new_str = str(value) if isinstance(value, Decimal) else value
                changes[field] = {"old": old_str, "new": new_str}
                setattr(subcontractor, field, value)

        if changes:
            await self.db.flush()
            await self.db.refresh(subcontractor)

            # Audit trail
            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_type="subcontractor",
                entity_id=subcontractor.id,
                changes=changes,
            )

        return subcontractor

    async def delete_subcontractor(self, subcontractor_id: UUID) -> bool:
        """Delete subcontractor.

        Args:
            subcontractor_id: Subcontractor UUID

        Returns:
            True if deleted, False if not found
        """
        subcontractor = await self.get_subcontractor_by_id(subcontractor_id)
        if not subcontractor:
            return False

        # Audit trail before deletion
        await self._create_audit_log(
            action=AuditAction.DELETE,
            entity_type="subcontractor",
            entity_id=subcontractor.id,
            changes={"deleted_name": subcontractor.name},
        )

        await self.db.delete(subcontractor)
        await self.db.flush()

        return True

    # --- Subcontract methods ---

    async def create_subcontract(
        self, order_id: UUID, subcontract_data: SubcontractCreate
    ) -> Subcontract:
        """Create a new subcontract for an order.

        Args:
            order_id: Order UUID
            subcontract_data: Subcontract creation data

        Returns:
            Created subcontract instance
        """
        subcontract = Subcontract(order_id=order_id, **subcontract_data.model_dump())
        self.db.add(subcontract)
        await self.db.flush()
        await self.db.refresh(subcontract)

        # Audit trail (convert Decimals to str for JSON serialization)
        changes_dict = subcontract_data.model_dump()
        for key, value in changes_dict.items():
            if isinstance(value, Decimal):
                changes_dict[key] = str(value)

        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_type="subcontract",
            entity_id=subcontract.id,
            changes={"created": changes_dict, "order_id": str(order_id)},
        )

        return subcontract

    async def get_subcontract_by_id(self, subcontract_id: UUID) -> Subcontract | None:
        """Get subcontract by ID.

        Args:
            subcontract_id: Subcontract UUID

        Returns:
            Subcontract instance or None if not found
        """
        result = await self.db.execute(
            select(Subcontract).where(Subcontract.id == subcontract_id)
        )
        return result.scalar_one_or_none()

    async def get_subcontracts_by_order(self, order_id: UUID) -> list[Subcontract]:
        """Get all subcontracts for an order.

        Args:
            order_id: Order UUID

        Returns:
            List of subcontract instances
        """
        result = await self.db.execute(
            select(Subcontract)
            .where(Subcontract.order_id == order_id)
            .order_by(Subcontract.created_at)
        )
        return list(result.scalars().all())

    async def update_subcontract(
        self,
        subcontract_id: UUID,
        subcontract_data: SubcontractUpdate,
    ) -> Subcontract | None:
        """Update subcontract.

        Args:
            subcontract_id: Subcontract UUID
            subcontract_data: Subcontract update data

        Returns:
            Updated subcontract instance or None if not found
        """
        subcontract = await self.get_subcontract_by_id(subcontract_id)
        if not subcontract:
            return None

        # Track changes for audit
        changes: dict[str, object] = {}
        update_data = subcontract_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            old_value = getattr(subcontract, field)
            if old_value != value:
                # Convert Decimals and UUIDs to str for JSON serialization
                old_str = str(old_value) if isinstance(old_value, (Decimal, UUID)) else old_value
                new_str = str(value) if isinstance(value, (Decimal, UUID)) else value
                changes[field] = {"old": old_str, "new": new_str}
                setattr(subcontract, field, value)

        if changes:
            await self.db.flush()
            await self.db.refresh(subcontract)

            # Audit trail
            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_type="subcontract",
                entity_id=subcontract.id,
                changes=changes,
            )

        return subcontract

    async def delete_subcontract(self, subcontract_id: UUID) -> bool:
        """Delete subcontract.

        Args:
            subcontract_id: Subcontract UUID

        Returns:
            True if deleted, False if not found
        """
        subcontract = await self.get_subcontract_by_id(subcontract_id)
        if not subcontract:
            return False

        # Audit trail before deletion
        await self._create_audit_log(
            action=AuditAction.DELETE,
            entity_type="subcontract",
            entity_id=subcontract.id,
            changes={"deleted_order_id": str(subcontract.order_id)},
        )

        await self.db.delete(subcontract)
        await self.db.flush()

        return True
