"""Document generation service using Jinja2 templates and WeasyPrint PDF."""

import logging
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.calculation import Calculation, CalculationStatus
from app.models.order import Order

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

# Company info constant (Infer s.r.o.)
COMPANY_INFO = {
    "name": "Infer s.r.o.",
    "ico": "04856562",
    "dic": "CZ04856562",
    "address": "Průmyslová 1, 741 01 Nový Jičín",
    "phone": "+420 xxx xxx xxx",
    "email": "info@infer.cz",
    "bank": "CZ00 0000 0000 0000 0000 0000",
    "bank_name": "Fio banka, a.s.",
    "bank_account": "2501234567/2010",
    "iban": "CZ65 2010 0000 0025 0123 4567",
    "swift": "FIOBCZPPXXX",
}

INVOICE_TYPE_LABELS = {
    "final": "Faktura",
    "advance": "Zálohová faktura",
    "proforma": "Proforma faktura",
}


def _get_jinja_env() -> Environment:
    """Get configured Jinja2 environment."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )


def _format_price(value: Decimal | float | None) -> str:
    """Format price in Czech format."""
    if value is None:
        return "0,00"
    return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")


class DocumentGeneratorService:
    """Service for generating PDF documents from templates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_offer_pdf(
        self,
        order_id: UUID,
        valid_days: int = 30,
        note: str | None = None,
    ) -> bytes:
        """Generate offer PDF for an order.

        Args:
            order_id: Order UUID.
            valid_days: Offer validity period in days.
            note: Optional additional note.

        Returns:
            PDF file bytes.

        Raises:
            ValueError: If order or required data not found.
        """
        # Load order with customer and items
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Zakázka {order_id} nenalezena")

        if not order.customer:
            raise ValueError(f"Zakázka {order.number} nemá přiřazeného zákazníka")

        # Get latest approved calculation for pricing
        calc_result = await self.db.execute(
            select(Calculation)
            .where(
                Calculation.order_id == order_id,
            )
            .options(selectinload(Calculation.items))
            .order_by(Calculation.created_at.desc())
        )
        calculation = calc_result.scalars().first()

        # Prepare template context
        today = date.today()
        valid_until = today + timedelta(days=valid_days)

        context = {
            "order": order,
            "customer": order.customer,
            "items": order.items,
            "calculation": calculation,
            "today": today.strftime("%d.%m.%Y"),
            "valid_until": valid_until.strftime("%d.%m.%Y"),
            "valid_days": valid_days,
            "note": note,
            "format_price": _format_price,
            "total_price": _format_price(calculation.total_price) if calculation else "Dle kalkulace",
            "company": {
                "name": "Infer s.r.o.",
                "ico": "04856562",
                "dic": "CZ04856562",
                "address": "Průmyslová 1, 741 01 Nový Jičín",
                "phone": "+420 xxx xxx xxx",
                "email": "info@infer.cz",
                "bank": "CZ00 0000 0000 0000 0000 0000",
            },
        }

        # Render HTML template
        env = _get_jinja_env()
        template = env.get_template("nabidka.html")
        html_content = template.render(**context)

        # Generate PDF
        from weasyprint import HTML  # type: ignore

        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        logger.info("document_generator.offer_generated order_id=%s", order_id)
        return pdf_bytes

    async def generate_production_sheet_pdf(
        self,
        order_id: UUID,
        include_controls: bool = True,
        note: str | None = None,
    ) -> bytes:
        """Generate production sheet (průvodka) PDF for an order.

        Args:
            order_id: Order UUID.
            include_controls: Include quality control checkpoints.
            note: Optional additional note.

        Returns:
            PDF file bytes.

        Raises:
            ValueError: If order not found.
        """
        # Load order with items and customer
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Zakázka {order_id} nenalezena")

        today = date.today()

        # Control checkpoints for ISO 9001
        control_points = []
        if include_controls:
            control_points = [
                {"name": "Kontrola vstupního materiálu", "responsible": "Skladník"},
                {"name": "Kontrola rozměrů po řezání", "responsible": "Dělník"},
                {"name": "Mezioperační kontrola svařování", "responsible": "Svářeč / NDT"},
                {"name": "Vizuální kontrola povrchu", "responsible": "Kontrolor"},
                {"name": "Rozměrová kontrola finálního výrobku", "responsible": "Kontrolor"},
                {"name": "Kontrola dokumentace a atestací", "responsible": "Vedoucí výroby"},
            ]

        context = {
            "order": order,
            "customer": order.customer,
            "items": order.items,
            "today": today.strftime("%d.%m.%Y"),
            "note": note,
            "control_points": control_points,
            "include_controls": include_controls,
            "company": {
                "name": "Infer s.r.o.",
                "ico": "04856562",
            },
        }

        env = _get_jinja_env()
        template = env.get_template("pruvodka.html")
        html_content = template.render(**context)

        from weasyprint import HTML

        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        logger.info("document_generator.production_sheet_generated order_id=%s", order_id)
        return pdf_bytes

    async def generate_dimensional_protocol(
        self,
        order_id: UUID,
    ) -> bytes:
        """Generate dimensional protocol (rozměrový protokol) PDF for an order.

        Args:
            order_id: Order UUID.

        Returns:
            PDF file bytes.

        Raises:
            ValueError: If order not found.
        """
        # Load order with items and customer
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Zakázka {order_id} nenalezena")

        today = date.today()

        # Generate protocol number (format: RP-YYYYMMDD-ORDER_NUMBER)
        protocol_number = f"RP-{today.strftime('%Y%m%d')}-{order.number}"

        context = {
            "order": order,
            "items": order.items,
            "today": today.strftime("%d.%m.%Y"),
            "protocol_number": protocol_number,
            "company": {
                "name": "Infer s.r.o.",
                "ico": "04856562",
                "dic": "CZ04856562",
                "address": "Průmyslová 1, 741 01 Nový Jičín",
                "phone": "+420 xxx xxx xxx",
                "email": "info@infer.cz",
            },
        }

        env = _get_jinja_env()
        template = env.get_template("protokol_rozmerovy.html")
        html_content = template.render(**context)

        from weasyprint import HTML

        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        logger.info("document_generator.dimensional_protocol_generated order_id=%s protocol_number=%s", order_id, protocol_number)
        return pdf_bytes

    async def generate_material_certificate(
        self,
        order_id: UUID,
        certificate_type: str = "3.1",
    ) -> bytes:
        """Generate material certificate (materiálový atest) PDF for an order.

        Args:
            order_id: Order UUID.
            certificate_type: Certificate type per EN 10-204 ("3.1" or "3.2").

        Returns:
            PDF file bytes.

        Raises:
            ValueError: If order not found or invalid certificate type.
        """
        if certificate_type not in ("3.1", "3.2"):
            raise ValueError(f"Neplatný typ atestu: {certificate_type}. Povolené hodnoty: 3.1, 3.2")

        # Load order with items and customer
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Zakázka {order_id} nenalezena")

        today = date.today()

        # Generate certificate number (format: MA-{TYPE}-YYYYMMDD-ORDER_NUMBER)
        cert_type_code = certificate_type.replace(".", "")
        certificate_number = f"MA-{cert_type_code}-{today.strftime('%Y%m%d')}-{order.number}"

        context = {
            "order": order,
            "items": order.items,
            "today": today.strftime("%d.%m.%Y"),
            "certificate_number": certificate_number,
            "certificate_type": certificate_type,
            "company": {
                "name": "Infer s.r.o.",
                "ico": "04856562",
                "dic": "CZ04856562",
                "address": "Průmyslová 1, 741 01 Nový Jičín",
                "phone": "+420 xxx xxx xxx",
                "email": "info@infer.cz",
            },
        }

        env = _get_jinja_env()
        template = env.get_template("atestace.html")
        html_content = template.render(**context)

        from weasyprint import HTML

        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        logger.info(
            "document_generator.material_certificate_generated order_id=%s certificate_number=%s type=%s",
            order_id,
            certificate_number,
            certificate_type,
        )
        return pdf_bytes

    async def _load_order_with_relations(self, order_id: UUID) -> Order:
        """Load order with customer and items, raise ValueError if not found."""
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Zakázka {order_id} nenalezena")
        if not order.customer:
            raise ValueError(f"Zakázka {order.number} nemá přiřazeného zákazníka")
        return order

    async def generate_invoice_pdf(
        self,
        order_id: UUID,
        invoice_type: str = "final",
        due_days: int = 14,
        note: str | None = None,
    ) -> bytes:
        """Generate invoice PDF for an order.

        Args:
            order_id: Order UUID.
            invoice_type: "final", "advance", or "proforma".
            due_days: Payment due in days.
            note: Optional additional note.

        Returns:
            PDF file bytes.
        """
        order = await self._load_order_with_relations(order_id)
        today = date.today()
        due_date_val = today + timedelta(days=due_days)

        # Generate invoice number
        type_prefix = {"final": "FV", "advance": "ZF", "proforma": "PF"}
        prefix = type_prefix.get(invoice_type, "FV")
        invoice_number = f"{prefix}-{today.strftime('%Y')}-{order.number}"
        variable_symbol = order.number.replace("-", "").replace("ZAK", "")

        # Get approved calculation for pricing
        calc_result = await self.db.execute(
            select(Calculation)
            .where(Calculation.order_id == order_id, Calculation.status == CalculationStatus.APPROVED)
            .options(selectinload(Calculation.items))
            .order_by(Calculation.updated_at.desc())
            .limit(1)
        )
        calculation = calc_result.scalar_one_or_none()

        # Build invoice items with prices
        invoice_items = []
        total_items = len(order.items)
        for item in order.items:
            if calculation and total_items > 0:
                item_share = float(calculation.total_price) / total_items
                unit_price = item_share / float(item.quantity) if item.quantity > 0 else item_share
            else:
                unit_price = 1000.00  # placeholder

            if invoice_type == "advance":
                unit_price *= 0.5  # 50% advance

            total_price = unit_price * float(item.quantity)
            invoice_items.append({
                "name": item.name,
                "material": item.material,
                "dn": item.dn,
                "pn": item.pn,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": unit_price,
                "total_price": total_price,
            })

        subtotal = sum(i["total_price"] for i in invoice_items)
        vat_amount = subtotal * 0.21
        total_with_vat = subtotal + vat_amount

        context = {
            "order": order,
            "customer": order.customer,
            "invoice_items": invoice_items,
            "invoice_number": invoice_number,
            "invoice_type": invoice_type,
            "invoice_type_label": INVOICE_TYPE_LABELS.get(invoice_type, "Faktura"),
            "issue_date": today.strftime("%d.%m.%Y"),
            "due_date": due_date_val.strftime("%d.%m.%Y"),
            "variable_symbol": variable_symbol,
            "subtotal": subtotal,
            "vat_amount": vat_amount,
            "total_with_vat": total_with_vat,
            "note": note,
            "format_price": _format_price,
            "today": today.strftime("%d.%m.%Y"),
            "company": COMPANY_INFO,
        }

        env = _get_jinja_env()
        template = env.get_template("faktura.html")
        html_content = template.render(**context)

        from weasyprint import HTML
        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        logger.info("document_generator.invoice_generated order_id=%s invoice_number=%s", order_id, invoice_number)
        return pdf_bytes

    async def generate_delivery_note_pdf(
        self,
        order_id: UUID,
        delivery_address: str | None = None,
        note: str | None = None,
    ) -> bytes:
        """Generate delivery note (dodací list) PDF for an order.

        Args:
            order_id: Order UUID.
            delivery_address: Optional delivery address override.
            note: Optional additional note.

        Returns:
            PDF file bytes.
        """
        order = await self._load_order_with_relations(order_id)
        today = date.today()
        delivery_number = f"DL-{today.strftime('%Y%m%d')}-{order.number}"

        context = {
            "order": order,
            "customer": order.customer,
            "items": order.items,
            "delivery_number": delivery_number,
            "delivery_address": delivery_address,
            "today": today.strftime("%d.%m.%Y"),
            "note": note,
            "company": COMPANY_INFO,
        }

        env = _get_jinja_env()
        template = env.get_template("dodaci_list.html")
        html_content = template.render(**context)

        from weasyprint import HTML
        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        logger.info("document_generator.delivery_note_generated order_id=%s delivery_number=%s", order_id, delivery_number)
        return pdf_bytes

    async def generate_order_confirmation_pdf(
        self,
        order_id: UUID,
        show_prices: bool = False,
        delivery_terms: str | None = None,
        payment_terms: str | None = None,
        note: str | None = None,
    ) -> bytes:
        """Generate order confirmation (potvrzení objednávky) PDF for an order.

        Args:
            order_id: Order UUID.
            show_prices: Whether to include price columns.
            delivery_terms: Optional delivery terms override.
            payment_terms: Optional payment terms override.
            note: Optional additional note.

        Returns:
            PDF file bytes.
        """
        order = await self._load_order_with_relations(order_id)
        today = date.today()
        due_date_str = order.due_date.strftime("%d.%m.%Y") if order.due_date else None

        # Optionally calculate prices
        total_price = None
        items_with_prices = order.items
        if show_prices:
            calc_result = await self.db.execute(
                select(Calculation)
                .where(Calculation.order_id == order_id, Calculation.status == CalculationStatus.APPROVED)
                .options(selectinload(Calculation.items))
                .order_by(Calculation.updated_at.desc())
                .limit(1)
            )
            calculation = calc_result.scalar_one_or_none()
            if calculation:
                total_price = calculation.total_price

        context = {
            "order": order,
            "customer": order.customer,
            "items": items_with_prices,
            "today": today.strftime("%d.%m.%Y"),
            "due_date": due_date_str,
            "show_prices": show_prices,
            "total_price": total_price,
            "delivery_terms": delivery_terms,
            "payment_terms": payment_terms,
            "note": note,
            "format_price": _format_price,
            "company": COMPANY_INFO,
        }

        env = _get_jinja_env()
        template = env.get_template("objednavka.html")
        html_content = template.render(**context)

        from weasyprint import HTML
        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        logger.info("document_generator.order_confirmation_generated order_id=%s", order_id)
        return pdf_bytes
