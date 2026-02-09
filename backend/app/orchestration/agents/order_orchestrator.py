"""Order Orchestrator - customer matching, order creation, document linking.

Orchestrates:
- Customer matching (ICO → email → name → create new)
- Order matching by reference or creation for poptavka/objednavka
- Document linking to orders
- InboxMessage status updates
- Next stage routing (calculate, notify, escalate)
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.customer import Customer
from app.models.document import Document
from app.models.inbox import InboxMessage, InboxStatus
from app.models.offer import Offer, OfferStatus
from app.models.operation import Operation, OperationStatus
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
                    await self._update_order_from_parsed_data(
                        session, matched_order_id, parsed_data
                    )
                    await self._create_default_operations(session, matched_order_id)

                inbox_msg.order_id = matched_order_id
                inbox_msg.customer_id = matched_customer_id
                inbox_msg.status = InboxStatus.PROCESSED
                await session.commit()

                next_stage = (
                    "production_started"
                    if classification == "objednavka"
                    else None
                )

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
                    "next_stage": next_stage,
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
            priority=self._map_urgency(parsed_data.get("urgency")),
            due_date=self._parse_deadline(parsed_data.get("deadline")),
            note=parsed_data.get("note") or parsed_data.get("description"),
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
    def _parse_deadline(deadline_text: str | None) -> date | None:
        """Parse deadline text into a date.

        Supports:
        - DD.MM.YYYY format
        - "X týdnů/týdny" (X weeks)
        - "X měsíců/měsíce" (X months)

        Returns None for vague texts like "co nejdříve".
        """
        if not deadline_text:
            return None

        text = deadline_text.strip().lower()

        # DD.MM.YYYY
        m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        if m:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                return None

        # X týdnů/týdny/týden/tydnu/tyden
        m = re.search(r"(\d+)\s*t[ýy]d[eě]?n", text)
        if m:
            weeks = int(m.group(1))
            return date.today() + timedelta(weeks=weeks)

        # X měsíců/měsíce/měsíc
        m = re.search(r"(\d+)\s*m[eě]s[ií]c", text)
        if m:
            months = int(m.group(1))
            return date.today() + timedelta(days=months * 30)

        return None

    @staticmethod
    def _map_urgency(urgency: str | None) -> OrderPriority:
        """Map urgency string from parser to OrderPriority enum."""
        if not urgency:
            return OrderPriority.NORMAL
        mapping = {
            "low": OrderPriority.LOW,
            "normal": OrderPriority.NORMAL,
            "high": OrderPriority.HIGH,
            "critical": OrderPriority.URGENT,
        }
        return mapping.get(urgency.lower(), OrderPriority.NORMAL)

    async def _update_order_from_parsed_data(
        self, session: AsyncSession, order_id: UUID, parsed_data: dict
    ) -> None:
        """Update existing order with deadline/priority/note from parsed email data."""
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return

        # Set due_date if not already set
        if parsed_data.get("deadline") and order.due_date is None:
            due = self._parse_deadline(parsed_data["deadline"])
            if due:
                order.due_date = due
                logger.info(
                    "order_due_date_set",
                    order_id=str(order_id),
                    due_date=str(due),
                )

        # Update priority if still NORMAL
        if parsed_data.get("urgency") and order.priority == OrderPriority.NORMAL:
            new_priority = self._map_urgency(parsed_data["urgency"])
            if new_priority != OrderPriority.NORMAL:
                order.priority = new_priority
                logger.info(
                    "order_priority_updated",
                    order_id=str(order_id),
                    priority=new_priority.value,
                )

        # Append note
        note_text = parsed_data.get("note")
        if note_text:
            if order.note:
                order.note = f"{order.note}\n---\n{note_text}"
            else:
                order.note = note_text

    async def _create_default_operations(
        self, session: AsyncSession, order_id: UUID
    ) -> None:
        """Create default production operations and advance order to VYROBA.

        Standard operations for Infer s.r.o. (pipe fittings, weldments):
        1. Material receipt & inspection
        2. Cutting & preparation
        3. Welding
        4. NDT inspection
        5. Surface treatment
        6. Final inspection & dispatch
        """
        # Check if operations already exist
        result = await session.execute(
            select(func.count()).select_from(Operation).where(
                Operation.order_id == order_id
            )
        )
        if result.scalar_one() > 0:
            return

        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return

        default_ops = [
            (1, "Příjem a kontrola materiálu", "Vstupní kontrola dle atestace EN 10204", 4),
            (2, "Řezání a příprava", "Řezání, úkosy, příprava polotovarů", 8),
            (3, "Svařování", "Svařování dle WPS, mezioperační kontrola", 24),
            (4, "NDT kontrola", "Nedestruktivní testování svarů", 8),
            (5, "Povrchová úprava", "Tryskání Sa 2.5 + nátěr dle specifikace", 8),
            (6, "Výstupní kontrola a expedice", "Rozměrová kontrola, dokumentace, balení", 4),
        ]

        # Schedule backwards from due_date (8h = 1 working day)
        hours_per_day = 8
        schedules: dict[int, tuple[datetime | None, datetime | None]] = {}
        if order.due_date:
            cursor = datetime.combine(order.due_date, datetime.min.time())
            for seq, _, _, hours in reversed(default_ops):
                days = max(1, -(-hours // hours_per_day))  # ceil division
                planned_end = cursor
                planned_start = cursor - timedelta(days=int(days))
                schedules[seq] = (planned_start, planned_end)
                cursor = planned_start

        for seq, name, description, hours in default_ops:
            p_start, p_end = schedules.get(seq, (None, None))
            op = Operation(
                order_id=order_id,
                name=name,
                description=description,
                sequence=seq,
                duration_hours=Decimal(hours),
                status=OperationStatus.PLANNED.value,
                planned_start=p_start,
                planned_end=p_end,
            )
            session.add(op)

        order.status = OrderStatus.VYROBA

        logger.info(
            "production_auto_started",
            order_id=str(order_id),
            operations_count=len(default_ops),
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
