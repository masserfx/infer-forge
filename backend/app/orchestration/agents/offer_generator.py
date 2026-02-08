"""Offer Generator - generates PDF and Pohoda XML for approved calculations.

Triggered after Calculation.status → APPROVED (manual approval).
Generates:
- PDF offer using DocumentGenerator (Jinja2 + WeasyPrint)
- Pohoda XML offer using PohodaXMLBuilder
- Creates Document record for PDF
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.integrations.pohoda.xml_builder import PohodaXMLBuilder
from app.models.calculation import Calculation, CalculationStatus
from app.models.document import Document, DocumentCategory
from app.models.offer import Offer, OfferStatus
from app.models.order import Order
from app.services.document_generator import DocumentGeneratorService

logger = structlog.get_logger(__name__)
settings = get_settings()


class OfferGenerator:
    """Generates offer documents from approved calculations.

    Responsibilities:
    - Generate PDF offer (via DocumentGeneratorService)
    - Generate Pohoda XML offer (via PohodaXMLBuilder)
    - Create Offer record
    - Create Document record for PDF
    - Save files to disk
    """

    async def generate(self, order_id: UUID, calculation_id: UUID) -> dict:
        """Generate offer PDF and Pohoda XML for an approved calculation.

        Args:
            order_id: Order UUID
            calculation_id: Calculation UUID (must be APPROVED status)

        Returns:
            dict with offer_pdf_path, pohoda_xml_path, document_id, offer_id

        Raises:
            ValueError: If calculation is not approved or data is missing
        """
        logger.info(
            "offer_generation_start",
            order_id=str(order_id),
            calculation_id=str(calculation_id),
        )

        async with AsyncSessionLocal() as session:
            # Load calculation with order and customer
            result = await session.execute(
                select(Calculation)
                .where(Calculation.id == calculation_id)
                .options(
                    selectinload(Calculation.order).selectinload(Order.customer),
                    selectinload(Calculation.items),
                )
            )
            calculation = result.scalar_one_or_none()
            if not calculation:
                raise ValueError(f"Calculation not found: {calculation_id}")

            if calculation.status != CalculationStatus.APPROVED:
                raise ValueError(
                    f"Calculation must be APPROVED, current status: {calculation.status.value}"
                )

            order = calculation.order
            if not order:
                raise ValueError(f"Calculation {calculation_id} has no associated order")

            customer = order.customer
            if not customer:
                raise ValueError(f"Order {order.number} has no associated customer")

            # Generate offer number
            offer_number = await self._generate_offer_number(session)

            # Create Offer record
            valid_until = date.today() + timedelta(days=30)
            offer = Offer(
                order_id=order_id,
                number=offer_number,
                total_price=calculation.total_price,
                valid_until=valid_until,
                status=OfferStatus.DRAFT,
            )
            session.add(offer)
            await session.flush()
            offer_id = offer.id

            # Update calculation status
            calculation.status = CalculationStatus.OFFERED

            await session.commit()

        # Generate PDF (outside session for file I/O)
        async with AsyncSessionLocal() as session:
            doc_gen_service = DocumentGeneratorService(session)
            pdf_bytes = await doc_gen_service.generate_offer_pdf(order_id, valid_days=30)

        # Save PDF to disk
        upload_dir = Path(settings.UPLOAD_DIR)
        offers_dir = upload_dir / "offers"
        offers_dir.mkdir(parents=True, exist_ok=True)
        pdf_filename = f"{offer_number}_nabidka.pdf"
        pdf_path = offers_dir / pdf_filename
        pdf_path.write_bytes(pdf_bytes)

        logger.info("offer_pdf_generated", path=str(pdf_path), size_bytes=len(pdf_bytes))

        # Generate Pohoda XML
        async with AsyncSessionLocal() as session:
            # Reload entities for XML builder
            result = await session.execute(
                select(Order)
                .where(Order.id == order_id)
                .options(
                    selectinload(Order.customer),
                    selectinload(Order.items),
                )
            )
            order = result.scalar_one()

            result = await session.execute(
                select(Offer).where(Offer.id == offer_id)
            )
            offer = result.scalar_one()

        xml_builder = PohodaXMLBuilder()
        xml_bytes = xml_builder.build_offer_xml(offer, order, order.customer)

        # Save XML to disk
        xml_filename = f"{offer_number}_pohoda.xml"
        xml_path = offers_dir / xml_filename
        xml_path.write_bytes(xml_bytes)

        logger.info("offer_xml_generated", path=str(xml_path), size_bytes=len(xml_bytes))

        # Create Document record for PDF
        async with AsyncSessionLocal() as session:
            document = Document(
                entity_type="offer",
                entity_id=offer_id,
                file_name=pdf_filename,
                file_path=str(pdf_path),
                mime_type="application/pdf",
                file_size=len(pdf_bytes),
                category=DocumentCategory.NABIDKA,
                description=f"Nabídka {offer_number} pro zákazníka {customer.company_name}",
                version=1,
            )
            session.add(document)
            await session.commit()
            document_id = document.id

        logger.info(
            "offer_generation_complete",
            offer_id=str(offer_id),
            offer_number=offer_number,
            document_id=str(document_id),
            pdf_path=str(pdf_path),
            xml_path=str(xml_path),
        )

        return {
            "offer_id": offer_id,
            "offer_number": offer_number,
            "offer_pdf_path": str(pdf_path),
            "pohoda_xml_path": str(xml_path),
            "document_id": document_id,
        }

    @staticmethod
    async def _generate_offer_number(session: AsyncSession) -> str:
        """Generate next offer number.

        Args:
            session: SQLAlchemy async session

        Returns:
            Offer number string (e.g., "NAB-000123")
        """
        result = await session.execute(
            select(Offer).order_by(Offer.created_at.desc()).limit(1)
        )
        last_offer = result.scalar_one_or_none()

        if last_offer:
            # Extract number from last offer (format: NAB-XXXXXX)
            try:
                last_num = int(last_offer.number.split("-")[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                # Fallback if format is unexpected
                next_num = 1
        else:
            next_num = 1

        return f"NAB-{next_num:06d}"
