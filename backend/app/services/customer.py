"""Customer business logic service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog, Customer
from app.schemas import CustomerCreate, CustomerUpdate


class CustomerService:
    """Service for managing customers with audit trail."""

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
        entity_id: UUID,
        changes: dict | None = None,
    ) -> None:
        """Create audit log entry.

        Args:
            action: Audit action type
            entity_id: ID of affected entity
            changes: Dictionary of changes made
        """
        audit = AuditLog(
            user_id=self.user_id,
            action=action,
            entity_type="customer",
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit)

    async def create(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer.

        Args:
            customer_data: Customer creation data

        Returns:
            Created customer instance
        """
        customer = Customer(**customer_data.model_dump())
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)

        # Audit trail
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_id=customer.id,
            changes={"created": customer_data.model_dump()},
        )

        return customer

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        """Get customer by ID.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer instance or None if not found
        """
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Customer]:
        """Get all customers with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of customer instances
        """
        result = await self.db.execute(
            select(Customer).order_by(Customer.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update(
        self,
        customer_id: UUID,
        customer_data: CustomerUpdate,
    ) -> Customer | None:
        """Update customer.

        Args:
            customer_id: Customer UUID
            customer_data: Customer update data

        Returns:
            Updated customer instance or None if not found
        """
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None

        # Track changes for audit
        changes: dict = {}
        update_data = customer_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            old_value = getattr(customer, field)
            if old_value != value:
                changes[field] = {"old": old_value, "new": value}
                setattr(customer, field, value)

        if changes:
            await self.db.flush()
            await self.db.refresh(customer)

            # Audit trail
            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_id=customer.id,
                changes=changes,
            )

        return customer

    async def delete(self, customer_id: UUID) -> bool:
        """Delete customer.

        Args:
            customer_id: Customer UUID

        Returns:
            True if deleted, False if not found
        """
        customer = await self.get_by_id(customer_id)
        if not customer:
            return False

        # Audit trail before deletion
        await self._create_audit_log(
            action=AuditAction.DELETE,
            entity_id=customer.id,
            changes={"deleted_company": customer.company_name},
        )

        await self.db.delete(customer)
        await self.db.flush()

        return True
