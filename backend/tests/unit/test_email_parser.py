"""Unit tests for email parser agent (mocked API)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.email_parser import (
    EmailParser,
    ParsedInquiry,
    ParsedItem,
    _str_or_none,
)


def _make_parse_block(
    company_name: str | None = "XYZ s.r.o.",
    contact_name: str | None = "Jan Novak",
    email: str | None = "jan@xyz.cz",
    phone: str | None = "+420 123 456 789",
    items: list | None = None,
    deadline: str | None = "do konce brezna",
    note: str | None = "Atest dle EN 10204 3.1",
) -> MagicMock:
    """Create a mock parse_inquiry tool_use content block."""
    if items is None:
        items = [
            {
                "name": "koleno 90",
                "material": "P235GH",
                "quantity": 50,
                "unit": "ks",
                "dimensions": "DN200 PN16",
            }
        ]
    block = MagicMock()
    block.type = "tool_use"
    block.name = "parse_inquiry"
    block.input = {
        "company_name": company_name,
        "contact_name": contact_name,
        "email": email,
        "phone": phone,
        "items": items,
        "deadline": deadline,
        "note": note,
    }
    return block


def _make_response(blocks: list) -> MagicMock:
    """Create a mock API response."""
    response = MagicMock()
    response.content = blocks
    return response


class TestParsedItem:
    """Tests for ParsedItem dataclass."""

    def test_full_item(self) -> None:
        """Test creating a fully specified item."""
        item = ParsedItem(
            name="koleno 90",
            material="P235GH",
            quantity=50.0,
            unit="ks",
            dimensions="DN200 PN16",
        )
        assert item.name == "koleno 90"
        assert item.material == "P235GH"
        assert item.quantity == 50.0

    def test_minimal_item(self) -> None:
        """Test creating an item with only name."""
        item = ParsedItem(name="svarenec")
        assert item.name == "svarenec"
        assert item.material is None
        assert item.quantity is None


class TestParsedInquiry:
    """Tests for ParsedInquiry dataclass."""

    def test_empty_inquiry(self) -> None:
        """Test creating an empty inquiry (parse failure)."""
        inquiry = ParsedInquiry()
        assert inquiry.company_name is None
        assert inquiry.items == []

    def test_full_inquiry(self) -> None:
        """Test creating a fully populated inquiry."""
        items = [ParsedItem(name="T-kus", material="1.4301", quantity=10)]
        inquiry = ParsedInquiry(
            company_name="ABC s.r.o.",
            contact_name="Petr Dvorak",
            email="petr@abc.cz",
            phone="+420 111 222 333",
            items=items,
            deadline="15.4.2025",
            note="NDT RT 100%",
        )
        assert inquiry.company_name == "ABC s.r.o."
        assert len(inquiry.items) == 1
        assert inquiry.items[0].name == "T-kus"


class TestStrOrNone:
    """Tests for _str_or_none helper."""

    def test_none_input(self) -> None:
        assert _str_or_none(None) is None

    def test_empty_string(self) -> None:
        assert _str_or_none("") is None

    def test_whitespace_string(self) -> None:
        assert _str_or_none("   ") is None

    def test_valid_string(self) -> None:
        assert _str_or_none("hello") == "hello"

    def test_numeric_input(self) -> None:
        assert _str_or_none(42) == "42"


class TestEmailParser:
    """Tests for EmailParser with mocked API."""

    @pytest.fixture
    def parser(self) -> EmailParser:
        """Create parser with test API key."""
        return EmailParser(api_key="test-key")

    async def test_parse_full_email(self, parser: EmailParser) -> None:
        """Test parsing a complete inquiry email."""
        mock_response = _make_response([_make_parse_block()])

        with patch.object(
            parser._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await parser.parse(
                subject="Poptavka - kolena",
                body="Dobry den, firma XYZ s.r.o. poptava...",
            )

        assert result.company_name == "XYZ s.r.o."
        assert result.contact_name == "Jan Novak"
        assert len(result.items) == 1
        assert result.items[0].name == "koleno 90"
        assert result.items[0].material == "P235GH"
        assert result.items[0].quantity == 50.0
        assert result.deadline == "do konce brezna"

    async def test_parse_multiple_items(self, parser: EmailParser) -> None:
        """Test parsing email with multiple items."""
        items = [
            {
                "name": "koleno 90",
                "material": "P235GH",
                "quantity": 50,
                "unit": "ks",
                "dimensions": "DN200",
            },
            {
                "name": "T-kus",
                "material": "1.4301",
                "quantity": 10,
                "unit": "ks",
                "dimensions": "DN150",
            },
            {
                "name": "priruba",
                "material": "S235JR",
                "quantity": 20,
                "unit": "ks",
                "dimensions": "DN200 PN16",
            },
        ]
        mock_response = _make_response(
            [
                _make_parse_block(items=items),
            ]
        )

        with patch.object(
            parser._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await parser.parse(
                subject="Poptavka",
                body="Prosim o nabidku na vice polozek...",
            )

        assert len(result.items) == 3
        assert result.items[0].name == "koleno 90"
        assert result.items[1].name == "T-kus"
        assert result.items[2].name == "priruba"

    async def test_parse_timeout(self, parser: EmailParser) -> None:
        """Test handling of API timeout."""
        with patch.object(
            parser._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=TimeoutError("Timeout"),
        ):
            result = await parser.parse(
                subject="Test",
                body="Test body",
            )

        assert result.company_name is None
        assert result.items == []

    async def test_parse_api_error(self, parser: EmailParser) -> None:
        """Test handling of generic API error."""
        with patch.object(
            parser._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API error"),
        ):
            result = await parser.parse(
                subject="Test",
                body="Test body",
            )

        assert isinstance(result, ParsedInquiry)
        assert result.items == []

    async def test_parse_no_tool_use_block(self, parser: EmailParser) -> None:
        """Test handling of response without tool_use block."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Some response"
        mock_response = _make_response([text_block])

        with patch.object(
            parser._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await parser.parse(
                subject="Test",
                body="Test body",
            )

        assert result.company_name is None
        assert result.items == []

    def test_build_user_message(self) -> None:
        """Test user message construction."""
        msg = EmailParser._build_user_message(
            subject="Poptavka",
            body="Kratky text",
        )
        assert "Poptavka" in msg
        assert "Kratky text" in msg

    def test_build_user_message_truncation(self) -> None:
        """Test that long body is truncated at 6000 chars."""
        long_body = "x" * 7000
        msg = EmailParser._build_user_message("Test", long_body)
        assert "[... text zkracen ...]" in msg
