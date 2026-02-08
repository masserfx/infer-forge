"""Service layer for operations (výrobní operace)."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Operation, Order
from app.schemas.operation import OperationCreate, OperationUpdate

logger = structlog.get_logger(__name__)


class OperationService:
    """Service for managing production operations on orders."""

    def __init__(self, db: AsyncSession, user_id: UUID | None = None):
        """Initialize service.

        Args:
            db: Database session
            user_id: ID of user performing operations (for audit trail)
        """
        self.db = db
        self.user_id = user_id

    async def get_by_order(self, order_id: UUID) -> list[Operation]:
        """Get all operations for an order, ordered by sequence.

        Args:
            order_id: Order ID

        Returns:
            List of operations sorted by sequence
        """
        logger.info("get_operations_by_order", order_id=str(order_id), user_id=str(self.user_id))

        result = await self.db.execute(
            select(Operation)
            .where(Operation.order_id == order_id)
            .order_by(Operation.sequence)
        )
        operations = result.scalars().all()

        logger.info(
            "operations_retrieved",
            order_id=str(order_id),
            count=len(operations),
            user_id=str(self.user_id),
        )
        return list(operations)

    async def get_by_id(self, operation_id: UUID) -> Operation | None:
        """Get operation by ID.

        Args:
            operation_id: Operation ID

        Returns:
            Operation if found, None otherwise
        """
        result = await self.db.execute(
            select(Operation)
            .where(Operation.id == operation_id)
            .options(selectinload(Operation.order))
        )
        return result.scalar_one_or_none()

    async def create(self, order_id: UUID, data: OperationCreate) -> Operation | None:
        """Create a new operation for an order.

        Args:
            order_id: Order ID
            data: Operation creation data

        Returns:
            Created operation, or None if order not found
        """
        logger.info(
            "create_operation",
            order_id=str(order_id),
            name=data.name,
            sequence=data.sequence,
            user_id=str(self.user_id),
        )

        # Check if order exists
        order_result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            logger.warning("order_not_found", order_id=str(order_id), user_id=str(self.user_id))
            return None

        operation = Operation(
            order_id=order_id,
            name=data.name,
            description=data.description,
            sequence=data.sequence,
            duration_hours=data.duration_hours,
            responsible=data.responsible,
            planned_start=data.planned_start,
            planned_end=data.planned_end,
            notes=data.notes,
        )

        self.db.add(operation)
        await self.db.commit()
        await self.db.refresh(operation)

        logger.info(
            "operation_created",
            operation_id=str(operation.id),
            order_id=str(order_id),
            name=data.name,
            user_id=str(self.user_id),
        )

        return operation

    async def update(self, operation_id: UUID, data: OperationUpdate) -> Operation | None:
        """Update an operation.

        Args:
            operation_id: Operation ID
            data: Update data

        Returns:
            Updated operation, or None if not found
        """
        logger.info(
            "update_operation",
            operation_id=str(operation_id),
            user_id=str(self.user_id),
        )

        operation = await self.get_by_id(operation_id)
        if not operation:
            logger.warning(
                "operation_not_found",
                operation_id=str(operation_id),
                user_id=str(self.user_id),
            )
            return None

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(operation, field, value)

        await self.db.commit()
        await self.db.refresh(operation)

        logger.info(
            "operation_updated",
            operation_id=str(operation_id),
            updated_fields=list(update_data.keys()),
            user_id=str(self.user_id),
        )

        return operation

    async def delete(self, operation_id: UUID) -> bool:
        """Delete an operation.

        Args:
            operation_id: Operation ID

        Returns:
            True if deleted, False if not found
        """
        logger.info(
            "delete_operation",
            operation_id=str(operation_id),
            user_id=str(self.user_id),
        )

        operation = await self.get_by_id(operation_id)
        if not operation:
            logger.warning(
                "operation_not_found",
                operation_id=str(operation_id),
                user_id=str(self.user_id),
            )
            return False

        await self.db.delete(operation)
        await self.db.commit()

        logger.info(
            "operation_deleted",
            operation_id=str(operation_id),
            user_id=str(self.user_id),
        )

        return True

    async def reorder(self, order_id: UUID, operation_ids: list[UUID]) -> list[Operation]:
        """Reorder operations by updating their sequence numbers.

        Args:
            order_id: Order ID
            operation_ids: List of operation IDs in new order

        Returns:
            List of operations with updated sequences

        Raises:
            ValueError: If operation IDs don't match existing operations for this order
        """
        logger.info(
            "reorder_operations",
            order_id=str(order_id),
            operation_count=len(operation_ids),
            user_id=str(self.user_id),
        )

        # Get existing operations
        existing_ops = await self.get_by_order(order_id)
        existing_ids = {op.id for op in existing_ops}
        provided_ids = set(operation_ids)

        # Validate that all provided IDs exist and belong to this order
        if existing_ids != provided_ids:
            missing = existing_ids - provided_ids
            extra = provided_ids - existing_ids
            logger.error(
                "reorder_validation_failed",
                order_id=str(order_id),
                missing_ids=[str(op_id) for op_id in missing],
                extra_ids=[str(op_id) for op_id in extra],
                user_id=str(self.user_id),
            )
            raise ValueError(
                f"Operation IDs mismatch. Missing: {missing}, Extra: {extra}"
            )

        # Update sequences
        operations_map = {op.id: op for op in existing_ops}
        for new_sequence, op_id in enumerate(operation_ids, start=1):
            operation = operations_map[op_id]
            operation.sequence = new_sequence

        await self.db.commit()

        # Return updated operations in new order
        updated_ops = await self.get_by_order(order_id)

        logger.info(
            "operations_reordered",
            order_id=str(order_id),
            operation_count=len(updated_ops),
            user_id=str(self.user_id),
        )

        return updated_ops
