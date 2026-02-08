"""Tests for Pohoda invoice XML generation."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from lxml import etree

from app.integrations.pohoda.xml_builder import NAMESPACES, PohodaXMLBuilder

# --- Fixtures ---


@pytest.fixture
def builder() -> PohodaXMLBuilder:
    """Create XML builder instance."""
    return PohodaXMLBuilder()


@pytest.fixture
def mock_customer() -> MagicMock:
    """Create mock customer for invoice tests."""
    customer = MagicMock()
    customer.id = uuid4()
    customer.company_name = "ACME Steel s.r.o."
    customer.ico = "87654321"
    customer.dic = "CZ87654321"
    customer.contact_name = "Petr Novák"
    customer.email = "petr@acme.cz"
    customer.phone = "+420987654321"
    customer.address = "Průmyslová 15\nOstrava\n70200"
    customer.pohoda_id = 42
    return customer


@pytest.fixture
def mock_order_with_items(mock_customer: MagicMock) -> MagicMock:
    """Create mock order with items for invoice tests."""
    order = MagicMock()
    order.id = uuid4()
    order.number = "ZAK-2025-042"
    order.created_at = datetime(2025, 7, 15, 9, 0, tzinfo=UTC)
    order.due_date = date(2025, 9, 15)
    order.note = "Potrubní díly dle výkresu X42"
    order.customer = mock_customer

    # Order items with all fields
    item1 = MagicMock()
    item1.name = "Koleno 90° DN100"
    item1.material = "P265GH"
    item1.quantity = Decimal("10.00")
    item1.unit = "ks"
    item1.dn = "100"
    item1.pn = "16"
    item1.note = "Dle výkresu X42-01"

    item2 = MagicMock()
    item2.name = "Příruba DN200"
    item2.material = "S235JR"
    item2.quantity = Decimal("20.00")
    item2.unit = "ks"
    item2.dn = "200"
    item2.pn = "10"
    item2.note = None

    item3 = MagicMock()
    item3.name = "Redukce"
    item3.material = None
    item3.quantity = Decimal("5.00")
    item3.unit = "ks"
    item3.dn = None
    item3.pn = None
    item3.note = None

    order.items = [item1, item2, item3]
    return order


# --- Invoice XML Builder Tests ---


class TestPohodaInvoiceXMLBuilder:
    """Tests for Pohoda invoice XML generation."""

    def test_build_invoice_xml_encoding(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice XML must be encoded in Windows-1250."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        assert b"Windows-1250" in xml_bytes

    def test_build_invoice_xml_valid_structure(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice XML must be well-formed and contain required elements."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        # Check dataPack attributes
        assert root.get("ico") == "04856562"
        assert root.get("application") == "INFER_FORGE"
        assert root.get("version") == "2.0"

        # Check invoice element exists
        invoice = root.find(f".//{{{NAMESPACES['inv']}}}invoice")
        assert invoice is not None

    def test_build_invoice_xml_invoice_type(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice must have type 'issuedInvoice'."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        invoice_type = root.find(f".//{{{NAMESPACES['inv']}}}invoiceType")
        assert invoice_type is not None
        assert invoice_type.text == "issuedInvoice"

    def test_build_invoice_xml_invoice_number(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice must contain correct invoice number."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        xml_str = xml_bytes.decode("Windows-1250")

        assert "FV-2025-042" in xml_str

    def test_build_invoice_xml_dates(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice must contain issue date and due date."""
        invoice_date = date(2025, 7, 20)
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
            invoice_date=invoice_date,
            due_days=14,
        )
        root = etree.fromstring(xml_bytes)

        date_elem = root.find(f".//{{{NAMESPACES['inv']}}}date")
        assert date_elem is not None
        assert date_elem.text == "2025-07-20"

        due_date_elem = root.find(f".//{{{NAMESPACES['inv']}}}dateDue")
        assert due_date_elem is not None
        assert due_date_elem.text == "2025-08-03"  # 14 days later

    def test_build_invoice_xml_default_date_today(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice without explicit date should use today."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        date_elem = root.find(f".//{{{NAMESPACES['inv']}}}date")
        assert date_elem is not None
        assert date_elem.text == date.today().isoformat()

    def test_build_invoice_xml_description_text(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice text should include order number and note."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        xml_str = xml_bytes.decode("Windows-1250")

        assert "Faktura za zakázku ZAK-2025-042" in xml_str
        assert "Potrubní díly" in xml_str  # From order note

    def test_build_invoice_xml_customer_identity(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice must contain customer identity with ICO, DIC."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        xml_str = xml_bytes.decode("Windows-1250")

        assert "ACME Steel s.r.o." in xml_str
        assert "87654321" in xml_str  # ICO
        assert "CZ87654321" in xml_str  # DIC
        assert "Průmyslová 15" in xml_str  # Street
        assert "Ostrava" in xml_str  # City

    def test_build_invoice_xml_items_count(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice must contain all order items."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        items = root.findall(f".//{{{NAMESPACES['inv']}}}invoiceItem")
        assert len(items) == 3

    def test_build_invoice_xml_item_details(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice items must contain name, material, DN, PN."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        xml_str = xml_bytes.decode("Windows-1250")

        # First item
        assert "Koleno 90° DN100" in xml_str
        assert "Mat: P265GH" in xml_str
        assert "DN100" in xml_str
        assert "PN16" in xml_str

        # Second item
        assert "Příruba DN200" in xml_str
        assert "Mat: S235JR" in xml_str
        assert "DN200" in xml_str

        # Third item (minimal data)
        assert "Redukce" in xml_str

    def test_build_invoice_xml_item_quantity_unit(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice items must contain quantity and unit."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        # Check first item
        items = root.findall(f".//{{{NAMESPACES['inv']}}}invoiceItem")
        first_item = items[0]

        quantity = first_item.find(f".//{{{NAMESPACES['inv']}}}quantity")
        assert quantity is not None
        assert quantity.text == "10.00"

        unit = first_item.find(f".//{{{NAMESPACES['inv']}}}unit")
        assert unit is not None
        assert unit.text == "ks"

    def test_build_invoice_xml_vat_rate(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice items must have VAT rate 'high' (21% in CZ)."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        vat_rates = root.findall(f".//{{{NAMESPACES['inv']}}}rateVAT")
        assert len(vat_rates) == 3  # One per item
        for vat_rate in vat_rates:
            assert vat_rate.text == "high"

    def test_build_invoice_xml_unit_prices(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice items must contain unit prices in homeCurrency."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        # Check that unit prices exist (currently placeholders)
        unit_prices = root.findall(f".//{{{NAMESPACES['typ']}}}unitPrice")
        assert len(unit_prices) == 3  # One per item
        for unit_price in unit_prices:
            assert unit_price.text is not None
            assert Decimal(unit_price.text) > 0

    def test_build_invoice_xml_summary_rounding(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice summary must have rounding method 'math2one'."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        rounding = root.find(f".//{{{NAMESPACES['inv']}}}roundingDocument")
        assert rounding is not None
        assert rounding.text == "math2one"

    def test_build_invoice_xml_custom_due_days(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice should support custom due_days parameter."""
        invoice_date = date(2025, 7, 20)
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
            invoice_date=invoice_date,
            due_days=30,
        )
        root = etree.fromstring(xml_bytes)

        due_date_elem = root.find(f".//{{{NAMESPACES['inv']}}}dateDue")
        assert due_date_elem is not None
        assert due_date_elem.text == "2025-08-19"  # 30 days later

    def test_build_invoice_xml_without_order_note(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice should handle order without note."""
        mock_order_with_items.note = None

        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        xml_str = xml_bytes.decode("Windows-1250")

        assert "Faktura za zakázku ZAK-2025-042" in xml_str
        # Should still be valid XML
        root = etree.fromstring(xml_bytes)
        assert root is not None

    def test_build_invoice_xml_namespace_consistency(
        self,
        builder: PohodaXMLBuilder,
        mock_order_with_items: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Invoice XML must use consistent namespaces."""
        xml_bytes = builder.build_invoice_xml(
            order=mock_order_with_items,
            customer=mock_customer,
            invoice_number="FV-2025-042",
        )
        root = etree.fromstring(xml_bytes)

        # Check namespace declarations
        nsmap = root.nsmap
        assert "inv" in nsmap.values() or NAMESPACES["inv"] in nsmap.values()
        assert "typ" in nsmap.values() or NAMESPACES["typ"] in nsmap.values()
