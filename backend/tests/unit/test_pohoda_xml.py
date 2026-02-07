"""Tests for Pohoda XML builder, parser, and validator."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from lxml import etree

from app.integrations.pohoda.exceptions import PohodaXMLError
from app.integrations.pohoda.xml_builder import NAMESPACES, PohodaXMLBuilder
from app.integrations.pohoda.xml_parser import (
    PohodaResponseItem,
    PohodaXMLParser,
)
from app.integrations.pohoda.xsd_validator import XSDValidator

# --- Fixtures ---


@pytest.fixture
def builder() -> PohodaXMLBuilder:
    """Create XML builder instance."""
    return PohodaXMLBuilder()


@pytest.fixture
def mock_customer() -> MagicMock:
    """Create mock customer for XML tests."""
    customer = MagicMock()
    customer.id = uuid4()
    customer.company_name = "Test Company s.r.o."
    customer.ico = "12345678"
    customer.dic = "CZ12345678"
    customer.contact_name = "Jan Novák"
    customer.email = "jan@test.cz"
    customer.phone = "+420123456789"
    customer.address = "Hlavní 1\nPraha\n10000"
    customer.pohoda_id = None
    return customer


@pytest.fixture
def mock_order(mock_customer: MagicMock) -> MagicMock:
    """Create mock order for XML tests."""
    order = MagicMock()
    order.id = uuid4()
    order.number = "ZAK-2025-001"
    order.created_at = datetime(2025, 6, 15, 10, 30, tzinfo=UTC)
    order.due_date = date(2025, 9, 30)
    order.note = "Testovací zakázka"
    order.customer = mock_customer

    # Order items
    item1 = MagicMock()
    item1.name = "Koleno DN100"
    item1.material = "P265GH"
    item1.quantity = Decimal("5.00")
    item1.unit = "ks"
    item1.dn = "100"
    item1.pn = "16"
    item1.note = "Dle výkresu 001"

    item2 = MagicMock()
    item2.name = "Příruba DN200"
    item2.material = None
    item2.quantity = Decimal("10.00")
    item2.unit = "ks"
    item2.dn = "200"
    item2.pn = None
    item2.note = None

    order.items = [item1, item2]
    return order


@pytest.fixture
def mock_offer(mock_order: MagicMock) -> MagicMock:
    """Create mock offer for XML tests."""
    offer = MagicMock()
    offer.id = uuid4()
    offer.number = "NAB-2025-001"
    offer.total_price = Decimal("125000.50")
    offer.valid_until = date(2025, 8, 31)
    offer.created_at = datetime(2025, 6, 20, 14, 0, tzinfo=UTC)
    offer.order = mock_order
    return offer


# --- XML Builder Tests ---


class TestPohodaXMLBuilder:
    """Tests for Pohoda XML builder."""

    def test_build_customer_xml_encoding(
        self, builder: PohodaXMLBuilder, mock_customer: MagicMock
    ) -> None:
        """XML must be encoded in Windows-1250."""
        xml_bytes = builder.build_customer_xml(mock_customer)
        assert b"Windows-1250" in xml_bytes

    def test_build_customer_xml_valid(
        self, builder: PohodaXMLBuilder, mock_customer: MagicMock
    ) -> None:
        """Customer XML must be well-formed and contain required elements."""
        xml_bytes = builder.build_customer_xml(mock_customer)
        root = etree.fromstring(xml_bytes)

        # Check dataPack attributes
        assert root.get("ico") == "04856562"
        assert root.get("application") == "INFER_FORGE"
        assert root.get("version") == "2.0"

    def test_build_customer_xml_contains_data(
        self, builder: PohodaXMLBuilder, mock_customer: MagicMock
    ) -> None:
        """Customer XML must contain company info."""
        xml_bytes = builder.build_customer_xml(mock_customer)
        xml_str = xml_bytes.decode("Windows-1250")

        assert "Test Company s.r.o." in xml_str
        assert "12345678" in xml_str
        assert "CZ12345678" in xml_str
        assert "jan@test.cz" in xml_str

    def test_build_customer_xml_without_optional_fields(
        self, builder: PohodaXMLBuilder, mock_customer: MagicMock
    ) -> None:
        """Customer XML should handle missing optional fields."""
        mock_customer.dic = None
        mock_customer.phone = None
        mock_customer.address = None

        xml_bytes = builder.build_customer_xml(mock_customer)
        root = etree.fromstring(xml_bytes)
        assert root is not None

    def test_build_customer_xml_update_action(
        self, builder: PohodaXMLBuilder, mock_customer: MagicMock
    ) -> None:
        """Existing Pohoda customer should use update action."""
        mock_customer.pohoda_id = 12345

        xml_bytes = builder.build_customer_xml(mock_customer)
        xml_str = xml_bytes.decode("Windows-1250")
        assert "update" in xml_str

    def test_build_order_xml_encoding(
        self,
        builder: PohodaXMLBuilder,
        mock_order: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Order XML must be encoded in Windows-1250."""
        xml_bytes = builder.build_order_xml(mock_order, mock_customer)
        assert b"Windows-1250" in xml_bytes

    def test_build_order_xml_contains_data(
        self,
        builder: PohodaXMLBuilder,
        mock_order: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Order XML must contain order number, items, and customer info."""
        xml_bytes = builder.build_order_xml(mock_order, mock_customer)
        xml_str = xml_bytes.decode("Windows-1250")

        assert "ZAK-2025-001" in xml_str
        assert "Test Company s.r.o." in xml_str
        assert "Koleno DN100" in xml_str
        assert "DN100" in xml_str
        assert "PN16" in xml_str

    def test_build_order_xml_items_count(
        self,
        builder: PohodaXMLBuilder,
        mock_order: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Order XML must contain all items."""
        xml_bytes = builder.build_order_xml(mock_order, mock_customer)
        root = etree.fromstring(xml_bytes)

        # Find all orderItem elements
        items = root.findall(f".//{{{NAMESPACES['ord']}}}orderItem")
        assert len(items) == 2

    def test_build_order_xml_due_date(
        self,
        builder: PohodaXMLBuilder,
        mock_order: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Order XML must contain due date when present."""
        xml_bytes = builder.build_order_xml(mock_order, mock_customer)
        xml_str = xml_bytes.decode("Windows-1250")
        assert "2025-09-30" in xml_str

    def test_build_offer_xml_encoding(
        self,
        builder: PohodaXMLBuilder,
        mock_offer: MagicMock,
        mock_order: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Offer XML must be encoded in Windows-1250."""
        xml_bytes = builder.build_offer_xml(mock_offer, mock_order, mock_customer)
        assert b"Windows-1250" in xml_bytes

    def test_build_offer_xml_contains_data(
        self,
        builder: PohodaXMLBuilder,
        mock_offer: MagicMock,
        mock_order: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Offer XML must contain offer number, price, and validity."""
        xml_bytes = builder.build_offer_xml(mock_offer, mock_order, mock_customer)
        xml_str = xml_bytes.decode("Windows-1250")

        assert "NAB-2025-001" in xml_str
        assert "125000.50" in xml_str
        assert "2025-08-31" in xml_str

    def test_build_offer_xml_items_from_order(
        self,
        builder: PohodaXMLBuilder,
        mock_offer: MagicMock,
        mock_order: MagicMock,
        mock_customer: MagicMock,
    ) -> None:
        """Offer XML items should come from related order."""
        xml_bytes = builder.build_offer_xml(mock_offer, mock_order, mock_customer)
        root = etree.fromstring(xml_bytes)

        items = root.findall(f".//{{{NAMESPACES['ofr']}}}offerItem")
        assert len(items) == 2


# --- XML Parser Tests ---


class TestPohodaXMLParser:
    """Tests for Pohoda XML response parser."""

    def _build_response_xml(
        self,
        items: list[tuple[str, str, str]],
        pack_id: str = "001",
    ) -> bytes:
        """Build mock Pohoda response XML.

        Args:
            items: List of (state, note, id) tuples.
            pack_id: Response pack ID.

        Returns:
            XML bytes.
        """
        rsp_ns = "http://www.stormware.cz/schema/version_2/response.xsd"
        root = etree.Element(
            f"{{{rsp_ns}}}responsePack",
            nsmap={"rsp": rsp_ns},
            version="2.0",
            id=pack_id,
        )
        for state, note, item_id in items:
            pack_item = etree.SubElement(
                root,
                f"{{{rsp_ns}}}responsePackItem",
                version="2.0",
                id=f"item_{item_id}",
            )
            state_el = etree.SubElement(pack_item, f"{{{rsp_ns}}}state")
            state_el.text = state
            note_el = etree.SubElement(pack_item, f"{{{rsp_ns}}}note")
            note_el.text = note
            id_el = etree.SubElement(pack_item, f"{{{rsp_ns}}}id")
            id_el.text = item_id

        return etree.tostring(root, xml_declaration=True, encoding="Windows-1250")

    def test_parse_success_response(self) -> None:
        """Parser should correctly parse successful response."""
        xml_bytes = self._build_response_xml([("ok", "Záznam byl úspěšně vytvořen.", "12345")])
        result = PohodaXMLParser.parse_response(xml_bytes)

        assert result.success is True
        assert result.pack_id == "001"
        assert len(result.items) == 1
        assert result.items[0].state == "ok"
        assert result.items[0].id == "12345"
        assert result.items[0].is_success is True

    def test_parse_error_response(self) -> None:
        """Parser should correctly parse error response."""
        xml_bytes = self._build_response_xml([("error", "IČO nebylo nalezeno.", "")])
        result = PohodaXMLParser.parse_response(xml_bytes)

        assert result.success is False
        assert len(result.items) == 1
        assert result.items[0].state == "error"
        assert result.items[0].is_success is False

    def test_parse_multiple_items(self) -> None:
        """Parser should handle multiple response items."""
        xml_bytes = self._build_response_xml(
            [
                ("ok", "Vytvořeno.", "100"),
                ("ok", "Vytvořeno.", "101"),
                ("error", "Duplicitní záznam.", ""),
            ]
        )
        result = PohodaXMLParser.parse_response(xml_bytes)

        assert result.success is False  # One error -> not all ok
        assert len(result.items) == 3

    def test_parse_all_success(self) -> None:
        """All items ok -> overall success."""
        xml_bytes = self._build_response_xml(
            [
                ("ok", "OK", "100"),
                ("ok", "OK", "101"),
            ]
        )
        result = PohodaXMLParser.parse_response(xml_bytes)
        assert result.success is True

    def test_parse_invalid_xml(self) -> None:
        """Parser should raise PohodaXMLError for invalid XML."""
        with pytest.raises(PohodaXMLError):
            PohodaXMLParser.parse_response(b"not xml at all")

    def test_parse_empty_response(self) -> None:
        """Parser should handle response with no items."""
        rsp_ns = "http://www.stormware.cz/schema/version_2/response.xsd"
        root = etree.Element(
            f"{{{rsp_ns}}}responsePack",
            nsmap={"rsp": rsp_ns},
            version="2.0",
            id="empty",
        )
        xml_bytes = etree.tostring(root, xml_declaration=True, encoding="Windows-1250")

        result = PohodaXMLParser.parse_response(xml_bytes)
        assert result.success is False
        assert len(result.items) == 0

    def test_response_item_dataclass(self) -> None:
        """PohodaResponseItem should work as dataclass."""
        item = PohodaResponseItem(id="123", state="ok", note="Test")
        assert item.is_success is True
        assert item.id == "123"

        error_item = PohodaResponseItem(id="", state="error", note="Chyba")
        assert error_item.is_success is False


# --- XSD Validator Tests ---


class TestXSDValidator:
    """Tests for XSD validator."""

    def test_validate_wellformed_xml(self) -> None:
        """Well-formed XML should pass validation (no XSD available)."""
        validator = XSDValidator()
        xml = b'<?xml version="1.0" encoding="Windows-1250"?><root><child>test</child></root>'
        is_valid, errors = validator.validate(xml)
        assert is_valid is True
        assert errors == []

    def test_validate_malformed_xml(self) -> None:
        """Malformed XML should fail validation."""
        validator = XSDValidator()
        is_valid, errors = validator.validate(b"<root><unclosed>")
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_not_xml(self) -> None:
        """Non-XML content should fail validation."""
        validator = XSDValidator()
        is_valid, errors = validator.validate(b"just plain text")
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_string_method(self) -> None:
        """validate_string convenience method should work."""
        validator = XSDValidator()
        is_valid, errors = validator.validate_string("<root/>")
        assert is_valid is True

    def test_missing_xsd_directory_logs_warning(self) -> None:
        """Missing XSD directory should not crash, just log warning."""
        from pathlib import Path

        validator = XSDValidator(xsd_dir=Path("/nonexistent/xsd"))
        assert validator.schema is None

        # Should still validate well-formedness
        is_valid, _ = validator.validate(b"<root/>")
        assert is_valid is True
