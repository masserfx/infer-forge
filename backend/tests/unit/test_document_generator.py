"""Unit tests for document generator service."""

import sys
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calculation import (
    Calculation,
    CalculationItem,
    CalculationStatus,
    CostType,
)
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderPriority, OrderStatus
from app.services.document_generator import (
    DocumentGeneratorService,
    _format_price,
    _get_jinja_env,
)

# Mock weasyprint module so tests don't need system-level libpango
_mock_weasyprint = MagicMock()
_mock_html_instance = MagicMock()
_mock_html_instance.write_pdf.return_value = b"%PDF-1.4 mock pdf"
_mock_weasyprint.HTML.return_value = _mock_html_instance


@pytest.fixture
async def order_with_calculation(test_db: AsyncSession) -> tuple[Order, Calculation]:
    """Create an order with customer, items, and calculation."""
    customer = Customer(
        company_name="Test Steel s.r.o.",
        ico="12345678",
        dic="CZ12345678",
        contact_name="Jan Novak",
        email="jan@test-steel.cz",
        phone="+420 123 456 789",
        address="Brno, Česká republika",
    )
    test_db.add(customer)
    await test_db.flush()

    order = Order(
        customer_id=customer.id,
        number="ZK-2024-TEST",
        status=OrderStatus.NABIDKA,
        priority=OrderPriority.HIGH,
        note="Testovací zakázka pro generování dokumentů",
    )
    test_db.add(order)
    await test_db.flush()

    items = [
        OrderItem(
            order_id=order.id,
            name="Koleno 90° DN150 PN16",
            material="P265GH",
            quantity=Decimal("10"),
            unit="ks",
            dn="150",
            pn="16",
        ),
        OrderItem(
            order_id=order.id,
            name="Příruba plochá DN200 PN10",
            material="11 353",
            quantity=Decimal("20"),
            unit="ks",
            dn="200",
            pn="10",
        ),
    ]
    test_db.add_all(items)
    await test_db.flush()

    calculation = Calculation(
        order_id=order.id,
        name="Hlavní kalkulace",
        margin_percent=Decimal("15"),
        status=CalculationStatus.APPROVED,
        material_total=Decimal("3550"),
        labor_total=Decimal("34000"),
        cooperation_total=Decimal("0"),
        overhead_total=Decimal("12450"),
        margin_amount=Decimal("7500"),
        total_price=Decimal("57500"),
    )
    test_db.add(calculation)
    await test_db.flush()

    calc_items = [
        CalculationItem(
            calculation_id=calculation.id,
            cost_type=CostType.MATERIAL,
            name="P265GH plech",
            quantity=Decimal("100"),
            unit="kg",
            unit_price=Decimal("35.50"),
            total_price=Decimal("3550"),
        ),
        CalculationItem(
            calculation_id=calculation.id,
            cost_type=CostType.LABOR,
            name="Svařování",
            quantity=Decimal("40"),
            unit="hod",
            unit_price=Decimal("850"),
            total_price=Decimal("34000"),
        ),
    ]
    test_db.add_all(calc_items)
    await test_db.flush()

    await test_db.refresh(order, ["items", "customer", "calculations"])
    await test_db.refresh(calculation, ["items"])

    return order, calculation


class TestFormatPrice:
    """Tests for _format_price helper."""

    def test_format_integer(self) -> None:
        """Test formatting whole number."""
        assert _format_price(Decimal("1000")) == "1 000,00"

    def test_format_decimal(self) -> None:
        """Test formatting decimal number."""
        assert _format_price(Decimal("12345.67")) == "12 345,67"

    def test_format_none(self) -> None:
        """Test formatting None."""
        assert _format_price(None) == "0,00"

    def test_format_zero(self) -> None:
        """Test formatting zero."""
        assert _format_price(Decimal("0")) == "0,00"

    def test_format_float(self) -> None:
        """Test formatting float."""
        assert _format_price(57500.0) == "57 500,00"

    def test_format_large_number(self) -> None:
        """Test formatting large number."""
        result = _format_price(Decimal("1234567.89"))
        assert "1 234 567,89" == result


class TestJinjaEnvironment:
    """Tests for Jinja2 environment setup."""

    def test_env_creation(self) -> None:
        """Test that Jinja2 environment is created."""
        env = _get_jinja_env()
        assert env is not None

    def test_templates_exist(self) -> None:
        """Test that required templates exist."""
        env = _get_jinja_env()
        template = env.get_template("nabidka.html")
        assert template is not None
        template = env.get_template("pruvodka.html")
        assert template is not None


class TestDocumentGeneratorService:
    """Tests for DocumentGeneratorService."""

    @pytest.fixture(autouse=True)
    def _mock_weasyprint(self) -> None:
        """Mock weasyprint module to avoid needing system-level libpango."""
        self.mock_html_class = MagicMock()
        self.mock_html_instance = MagicMock()
        self.mock_html_instance.write_pdf.return_value = b"%PDF-1.4 mock pdf"
        self.mock_html_class.return_value = self.mock_html_instance

        mock_module = MagicMock()
        mock_module.HTML = self.mock_html_class

        # Insert mock weasyprint into sys.modules
        original = sys.modules.get("weasyprint")
        sys.modules["weasyprint"] = mock_module
        yield
        # Restore
        if original is not None:
            sys.modules["weasyprint"] = original
        else:
            sys.modules.pop("weasyprint", None)

    async def test_generate_offer_pdf(
        self,
        test_db: AsyncSession,
        order_with_calculation: tuple[Order, Calculation],
    ) -> None:
        """Test offer PDF generation."""
        order, calculation = order_with_calculation

        service = DocumentGeneratorService(test_db)
        pdf_bytes = await service.generate_offer_pdf(order.id)

        assert pdf_bytes == b"%PDF-1.4 mock pdf"
        self.mock_html_class.assert_called_once()
        self.mock_html_instance.write_pdf.assert_called_once()

        # Verify template was rendered with correct data
        call_kwargs = self.mock_html_class.call_args
        html_string = call_kwargs.kwargs.get("string", "")
        assert "Test Steel s.r.o." in html_string
        assert "ZK-2024-TEST" in html_string

    async def test_generate_production_sheet_pdf(
        self,
        test_db: AsyncSession,
        order_with_calculation: tuple[Order, Calculation],
    ) -> None:
        """Test production sheet PDF generation."""
        order, calculation = order_with_calculation

        service = DocumentGeneratorService(test_db)
        pdf_bytes = await service.generate_production_sheet_pdf(order.id)

        assert pdf_bytes == b"%PDF-1.4 mock pdf"
        self.mock_html_class.assert_called_once()

        html_string = self.mock_html_class.call_args.kwargs.get("string", "")
        assert "ZK-2024-TEST" in html_string

    async def test_generate_offer_order_not_found(self, test_db: AsyncSession) -> None:
        """Test offer generation with non-existent order."""
        service = DocumentGeneratorService(test_db)
        with pytest.raises(ValueError, match="nenalezena"):
            await service.generate_offer_pdf(uuid.uuid4())

    async def test_generate_production_sheet_order_not_found(
        self, test_db: AsyncSession
    ) -> None:
        """Test production sheet generation with non-existent order."""
        service = DocumentGeneratorService(test_db)
        with pytest.raises(ValueError, match="nenalezena"):
            await service.generate_production_sheet_pdf(uuid.uuid4())

    async def test_generate_offer_with_custom_validity(
        self,
        test_db: AsyncSession,
        order_with_calculation: tuple[Order, Calculation],
    ) -> None:
        """Test offer generation with custom validity period."""
        order, calculation = order_with_calculation

        service = DocumentGeneratorService(test_db)
        pdf_bytes = await service.generate_offer_pdf(order.id, valid_days=60)

        assert pdf_bytes is not None
        self.mock_html_class.assert_called_once()

    async def test_generate_production_sheet_without_controls(
        self,
        test_db: AsyncSession,
        order_with_calculation: tuple[Order, Calculation],
    ) -> None:
        """Test production sheet without quality control points."""
        order, calculation = order_with_calculation

        service = DocumentGeneratorService(test_db)
        pdf_bytes = await service.generate_production_sheet_pdf(
            order.id, include_controls=False
        )

        assert pdf_bytes is not None
