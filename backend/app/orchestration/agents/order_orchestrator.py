"""Order Orchestrator - customer matching, order creation, document linking.

Orchestrates:
- Customer matching (ICO → email → name → create new)
- Order matching by reference or creation for poptavka/objednavka
- Document linking to orders
- InboxMessage status updates
- Next stage routing (calculate, notify, escalate)
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.customer import Customer
from app.models.document import Document
from app.models.inbox import InboxMessage, InboxStatus
from app.models.order import Order, OrderPriority, OrderStatus

logger = structlog.get_logger(__name__)


class OrderOrchestrator:
    """Orchestrates order creation and customer matching from parsed email data.

    Responsibilities:
    - Match or create customer
    - Match or create order
    - Link documents to order
    - Update InboxMessage with customer_id, order_id
    - Determine next processing stage
    """

    async def process(self, inbox_message_id: UUID, parsed_data: dict) -> dict:
        """Process inbox message: match/create customer, order, link documents.

        Args:
            inbox_message_id: InboxMessage UUID
            parsed_data: Parsed email data with fields:
                - ico: str | None
                - email: str | None
                - company_name: str | None
                - order_reference: str | None (existing order number)
                - classification: str (poptavka, objednavka, reklamace, etc.)
                Additional fields: contact_name, phone, address, description, items

        Returns:
            dict with customer_id, order_id, customer_created, order_created,
            documents_linked, next_stage
        """
        logger.info(
            "order_orchestration_start",
            inbox_message_id=str(inbox_message_id),
            classification=parsed_data.get("classification"),
        )

        async with AsyncSessionLocal() as session:
            # Load InboxMessage
            result = await session.execute(
                select(InboxMessage).where(InboxMessage.id == inbox_message_id)
            )
            inbox_msg = result.scalar_one_or_none()
            if not inbox_msg:
                raise ValueError(f"InboxMessage not found: {inbox_message_id}")

            # Match or create customer
            customer, customer_created = await self._match_or_create_customer(
                session, parsed_data, inbox_msg.from_email
            )

            # Match or create order
            order: Order | None = None
            order_created = False
            classification = parsed_data.get("classification", "").lower()

            # Try to match existing order by reference
            if parsed_data.get("order_reference"):
                order = await self._match_order_by_reference(
                    session, parsed_data["order_reference"], customer.id
                )

            # Create new order for poptavka or objednavka
            if not order and classification in {"poptavka", "objednavka"}:
                order = await self._create_order(session, customer.id, parsed_data)
                order_created = True

            # Link documents to order (if order exists)
            documents_linked = 0
            if order:
                documents_linked = await self._link_documents_to_order(
                    session, inbox_message_id, order.id
                )

            # Update InboxMessage with customer_id, order_id, status
            inbox_msg.customer_id = customer.id
            inbox_msg.order_id = order.id if order else None
            inbox_msg.status = (
                InboxStatus.PROCESSED if order else InboxStatus.ESCALATED
            )

            await session.commit()

        # Determine next stage
        next_stage = self._determine_next_stage(classification, order_created)

        logger.info(
            "order_orchestration_complete",
            inbox_message_id=str(inbox_message_id),
            customer_id=str(customer.id),
            order_id=str(order.id) if order else None,
            customer_created=customer_created,
            order_created=order_created,
            documents_linked=documents_linked,
            next_stage=next_stage,
        )

        return {
            "customer_id": customer.id,
            "order_id": order.id if order else None,
            "customer_created": customer_created,
            "order_created": order_created,
            "documents_linked": documents_linked,
            "next_stage": next_stage,
        }

    async def _match_or_create_customer(
        self, session: AsyncSession, parsed_data: dict, from_email: str
    ) -> tuple[Customer, bool]:
        """Match existing customer or create new one.

        Matching priority:
        1. ICO (exact match)
        2. Email (exact match)
        3. Company name (case-insensitive LIKE)
        4. Create new

        Args:
            session: SQLAlchemy async session
            parsed_data: Parsed email data
            from_email: Sender email address

        Returns:
            (Customer, created) tuple
        """
        # 1. Match by ICO
        if parsed_data.get("ico"):
            result = await session.execute(
                select(Customer).where(Customer.ico == parsed_data["ico"])
            )
            customer = result.scalar_one_or_none()
            if customer:
                logger.info("customer_matched_by_ico", customer_id=str(customer.id))
                return customer, False

        # 2. Match by email
        email = parsed_data.get("email") or from_email
        result = await session.execute(
            select(Customer).where(Customer.email == email)
        )
        customer = result.scalar_one_or_none()
        if customer:
            logger.info("customer_matched_by_email", customer_id=str(customer.id))
            return customer, False

        # 3. Match by company name (case-insensitive)
        if parsed_data.get("company_name"):
            result = await session.execute(
                select(Customer).where(
                    func.lower(Customer.company_name).like(
                        f"%{parsed_data['company_name'].lower()}%"
                    )
                )
            )
            customer = result.scalar_one_or_none()
            if customer:
                logger.info("customer_matched_by_name", customer_id=str(customer.id))
                return customer, False

        # 4. Create new customer
        # Derive company name from email domain if not provided
        company_name = parsed_data.get("company_name")
        if not company_name:
            domain = email.split("@")[-1] if "@" in email else "unknown"
            company_name = domain.split(".")[0].capitalize()

        customer = Customer(
            company_name=company_name,
            ico=parsed_data.get("ico") or f"X{abs(hash(email)) % 9999999:07d}",
            contact_name=parsed_data.get("contact_name") or "Neznámý kontakt",
            email=email,
            phone=parsed_data.get("phone"),
            address=parsed_data.get("address"),
            category="C",  # New customer
        )
        session.add(customer)
        await session.flush()

        logger.info("customer_created", customer_id=str(customer.id), email=email)
        return customer, True

    async def _match_order_by_reference(
        self, session: AsyncSession, order_reference: str, customer_id: UUID
    ) -> Order | None:
        """Match existing order by reference number.

        Args:
            session: SQLAlchemy async session
            order_reference: Order reference number
            customer_id: Customer UUID (for validation)

        Returns:
            Order or None
        """
        result = await session.execute(
            select(Order).where(
                Order.number == order_reference,
                Order.customer_id == customer_id,
            )
        )
        order = result.scalar_one_or_none()
        if order:
            logger.info(
                "order_matched_by_reference",
                order_id=str(order.id),
                order_number=order_reference,
            )
        return order

    async def _create_order(
        self, session: AsyncSession, customer_id: UUID, parsed_data: dict
    ) -> Order:
        """Create new order from parsed data.

        Args:
            session: SQLAlchemy async session
            customer_id: Customer UUID
            parsed_data: Parsed email data

        Returns:
            Created Order
        """
        # Generate order number (simple counter for now)
        result = await session.execute(
            select(func.count()).select_from(Order)
        )
        order_count = result.scalar_one()
        order_number = f"ORD-{order_count + 1:06d}"

        # Determine initial status from classification
        classification = parsed_data.get("classification", "").lower()
        if classification == "poptavka":
            status = OrderStatus.POPTAVKA
        elif classification == "objednavka":
            status = OrderStatus.OBJEDNAVKA
        else:
            status = OrderStatus.POPTAVKA  # Default

        order = Order(
            customer_id=customer_id,
            number=order_number,
            status=status,
            priority=OrderPriority.NORMAL,
            note=parsed_data.get("description"),
        )
        session.add(order)
        await session.flush()

        logger.info(
            "order_created",
            order_id=str(order.id),
            order_number=order_number,
            status=status.value,
        )
        return order

    async def _link_documents_to_order(
        self, session: AsyncSession, inbox_message_id: UUID, order_id: UUID
    ) -> int:
        """Link all documents from inbox message to order.

        Updates Document.entity_type = 'order', entity_id = order_id.

        Args:
            session: SQLAlchemy async session
            inbox_message_id: InboxMessage UUID
            order_id: Order UUID

        Returns:
            Number of documents linked
        """
        # Find all documents for this inbox message
        result = await session.execute(
            select(Document).where(
                Document.entity_type == "inbox_message",
                Document.entity_id == inbox_message_id,
            )
        )
        documents = result.scalars().all()

        # Update entity to order
        for doc in documents:
            doc.entity_type = "order"
            doc.entity_id = order_id

        logger.info(
            "documents_linked_to_order",
            order_id=str(order_id),
            document_count=len(documents),
        )
        return len(documents)

    @staticmethod
    def _determine_next_stage(classification: str, order_created: bool) -> str | None:
        """Determine next processing stage based on classification.

        Args:
            classification: Email classification
            order_created: Whether new order was created

        Returns:
            Next stage: "calculate", "notify", "escalate", or None
        """
        if classification == "poptavka" and order_created:
            return "calculate"
        elif classification == "objednavka":
            return "notify"
        elif classification == "reklamace":
            return "escalate"
        return None
