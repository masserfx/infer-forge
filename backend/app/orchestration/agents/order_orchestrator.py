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
from app.models.offer import Offer, OfferStatus
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

            # Thread-based order matching: if thread_id exists, look for
            # previous messages in the same thread that already have an order
            matched_order_id = None
            matched_customer_id = None

            if inbox_msg.thread_id:
                thread_result = await session.execute(
                    select(InboxMessage).where(
                        InboxMessage.thread_id == inbox_msg.thread_id,
                        InboxMessage.order_id.isnot(None),
                        InboxMessage.id != inbox_message_id,
                    ).limit(1)
                )
                thread_msg = thread_result.scalar_one_or_none()
                if thread_msg and thread_msg.order_id:
                    matched_order_id = thread_msg.order_id
                    matched_customer_id = thread_msg.customer_id

            # Fallback: try matching via references chain
            if not matched_order_id and inbox_msg.references_header:
                import re
                ref_pattern = re.compile(r"<([^>]+)>")
                ref_ids = ref_pattern.findall(inbox_msg.references_header)
                if ref_ids:
                    for ref_id in ref_ids:
                        ref_result = await session.execute(
                            select(InboxMessage).where(
                                InboxMessage.message_id == ref_id,
                                InboxMessage.order_id.isnot(None),
                            ).limit(1)
                        )
                        ref_msg = ref_result.scalar_one_or_none()
                        if ref_msg and ref_msg.order_id:
                            matched_order_id = ref_msg.order_id
                            matched_customer_id = ref_msg.customer_id
                            # Also set thread_id for future lookups
                            if not inbox_msg.thread_id:
                                inbox_msg.thread_id = ref_msg.thread_id
                            break

            if matched_order_id:
                classification = parsed_data.get("classification", "").lower()

                # Handle offer acceptance
                if classification == "objednavka":
                    await self._handle_offer_acceptance(session, matched_order_id)

                inbox_msg.order_id = matched_order_id
                inbox_msg.customer_id = matched_customer_id
                inbox_msg.status = InboxStatus.PROCESSED
                await session.commit()

                logger.info(
                    "order_matched_by_thread",
                    inbox_message_id=str(inbox_message_id),
                    thread_id=inbox_msg.thread_id,
                    order_id=str(matched_order_id),
                    offer_acceptance=classification == "objednavka",
                )

                return {
                    "customer_id": matched_customer_id,
                    "order_id": matched_order_id,
                    "customer_created": False,
                    "order_created": False,
                    "documents_linked": 0,
                    "next_stage": "notify" if classification == "objednavka" else None,
                    "matched_by": "thread",
                }

            # Dedup: if order already exists for this message, skip
            if inbox_msg.order_id:
                result = await session.execute(
                    select(Order).where(Order.id == inbox_msg.order_id)
                )
                existing_order = result.scalar_one_or_none()
                if existing_order:
                    logger.info(
                        "order_already_exists_for_message",
                        inbox_message_id=str(inbox_message_id),
                        order_id=str(existing_order.id),
                        order_number=existing_order.number,
                    )
                    return {
                        "customer_id": inbox_msg.customer_id,
                        "order_id": existing_order.id,
                        "customer_created": False,
                        "order_created": False,
                        "documents_linked": 0,
                        "next_stage": None,
                    }

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
        # Generate order number from MAX existing number to avoid collisions
        result = await session.execute(
            select(func.max(Order.number)).where(Order.number.like("ORD-%"))
        )
        max_number = result.scalar_one()
        if max_number:
            # Extract numeric part from "ORD-000015" → 15
            last_num = int(max_number.split("-")[1])
        else:
            last_num = 0
        order_number = f"ORD-{last_num + 1:06d}"

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

    async def _handle_offer_acceptance(
        self, session: AsyncSession, order_id: UUID
    ) -> None:
        """Handle offer acceptance: mark SENT offer as ACCEPTED and advance order status.

        Args:
            session: SQLAlchemy async session
            order_id: Order UUID whose offer should be accepted
        """
        # Find the latest SENT offer for this order
        result = await session.execute(
            select(Offer).where(
                Offer.order_id == order_id,
                Offer.status == OfferStatus.SENT,
            ).order_by(Offer.created_at.desc()).limit(1)
        )
        offer = result.scalar_one_or_none()
        if offer:
            offer.status = OfferStatus.ACCEPTED
            logger.info(
                "offer_accepted_via_email",
                offer_id=str(offer.id),
                offer_number=offer.number,
                order_id=str(order_id),
            )

        # Advance order status to OBJEDNAVKA if currently NABIDKA
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order_record = result.scalar_one_or_none()
        if order_record and order_record.status == OrderStatus.NABIDKA:
            order_record.status = OrderStatus.OBJEDNAVKA
            logger.info(
                "order_status_advanced",
                order_id=str(order_id),
                old_status="nabidka",
                new_status="objednavka",
            )

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
