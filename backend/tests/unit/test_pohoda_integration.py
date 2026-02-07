"""Unit tests for Pohoda integration components.

Tests cover:
- PohodaClient HTTP communication and retry logic
- PohodaXMLParser response parsing
- Exception handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.pohoda import (
    PohodaClient,
    PohodaConnectionError,
    PohodaError,
    PohodaResponse,
    PohodaResponseError,
    PohodaXMLError,
    PohodaXMLParser,
)

# ============================================================================
# Exception Tests
# ============================================================================


def test_pohoda_error_hierarchy():
    """Test that all exceptions inherit from PohodaError."""
    assert issubclass(PohodaConnectionError, PohodaError)
    assert issubclass(PohodaResponseError, PohodaError)
    assert issubclass(PohodaXMLError, PohodaError)


def test_pohoda_response_error_with_status_code():
    """Test PohodaResponseError stores HTTP status code."""
    error = PohodaResponseError("Server error", status_code=500)
    assert error.status_code == 500
    assert "Server error" in str(error)


def test_pohoda_response_error_without_status_code():
    """Test PohodaResponseError works without status code."""
    error = PohodaResponseError("Generic error")
    assert error.status_code is None


# ============================================================================
# XML Parser Tests
# ============================================================================


def test_parse_response_success():
    """Test parsing successful response with multiple items."""
    xml_str = """<?xml version="1.0" encoding="Windows-1250"?>
<rsp:responsePack xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
                  version="2.0" id="PACK123">
  <rsp:responsePackItem version="2.0" id="ITEM1">
    <rsp:state>ok</rsp:state>
    <rsp:note>Doklad vytvořen</rsp:note>
    <rsp:id>12345</rsp:id>
  </rsp:responsePackItem>
  <rsp:responsePackItem version="2.0" id="ITEM2">
    <rsp:state>ok</rsp:state>
    <rsp:note>Kontakt aktualizován</rsp:note>
    <rsp:id>67890</rsp:id>
  </rsp:responsePackItem>
</rsp:responsePack>"""
    xml = xml_str.encode("windows-1250")

    parser = PohodaXMLParser()
    response = parser.parse_response(xml)

    assert isinstance(response, PohodaResponse)
    assert response.pack_id == "PACK123"
    assert response.success is True
    assert len(response.items) == 2

    # First item
    assert response.items[0].id == "12345"
    assert response.items[0].state == "ok"
    assert "vytvořen" in response.items[0].note
    assert response.items[0].is_success is True

    # Second item
    assert response.items[1].id == "67890"
    assert response.items[1].state == "ok"
    assert response.items[1].is_success is True


def test_parse_response_error():
    """Test parsing response with error state."""
    xml_str = """<?xml version="1.0" encoding="Windows-1250"?>
<rsp:responsePack xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
                  version="2.0" id="ERR001">
  <rsp:responsePackItem version="2.0" id="FAIL1">
    <rsp:state>error</rsp:state>
    <rsp:note>Chybějící povinné pole IČO</rsp:note>
    <rsp:id></rsp:id>
  </rsp:responsePackItem>
</rsp:responsePack>"""
    xml = xml_str.encode("windows-1250")

    parser = PohodaXMLParser()
    response = parser.parse_response(xml)

    assert response.success is False
    assert len(response.items) == 1
    assert response.items[0].state == "error"
    assert response.items[0].is_success is False
    assert "IČO" in response.items[0].note
    assert response.items[0].id == ""


def test_parse_response_mixed_states():
    """Test response with both success and error items."""
    xml_str = """<?xml version="1.0" encoding="Windows-1250"?>
<rsp:responsePack xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
                  version="2.0" id="MIX123">
  <rsp:responsePackItem version="2.0" id="OK1">
    <rsp:state>ok</rsp:state>
    <rsp:note>OK</rsp:note>
    <rsp:id>111</rsp:id>
  </rsp:responsePackItem>
  <rsp:responsePackItem version="2.0" id="ERR1">
    <rsp:state>error</rsp:state>
    <rsp:note>Chyba validace</rsp:note>
    <rsp:id></rsp:id>
  </rsp:responsePackItem>
</rsp:responsePack>"""
    xml = xml_str.encode("windows-1250")

    parser = PohodaXMLParser()
    response = parser.parse_response(xml)

    assert response.success is False  # Overall success requires ALL ok
    assert len(response.items) == 2
    assert response.items[0].is_success is True
    assert response.items[1].is_success is False


def test_parse_response_invalid_xml():
    """Test parser raises PohodaXMLError on malformed XML."""
    invalid_xml = b"<not-valid-xml"

    parser = PohodaXMLParser()
    with pytest.raises(PohodaXMLError) as exc_info:
        parser.parse_response(invalid_xml)

    assert "XML syntax" in str(exc_info.value)


def test_parse_response_empty_items():
    """Test parsing response with no items."""
    xml = b"""<?xml version="1.0" encoding="Windows-1250"?>
<rsp:responsePack xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
                  version="2.0" id="EMPTY">
</rsp:responsePack>"""

    parser = PohodaXMLParser()
    response = parser.parse_response(xml)

    assert response.success is False  # Empty = failure
    assert len(response.items) == 0
    assert response.pack_id == "EMPTY"


def test_parse_response_preserves_raw_xml():
    """Test that parser preserves raw XML string."""
    xml = b"""<?xml version="1.0" encoding="Windows-1250"?>
<rsp:responsePack xmlns:rsp="http://www.stormware.cz/schema/version_2/response.xsd"
                  version="2.0" id="TEST">
  <rsp:responsePackItem version="2.0" id="ITEM1">
    <rsp:state>ok</rsp:state>
    <rsp:note>Test</rsp:note>
    <rsp:id>999</rsp:id>
  </rsp:responsePackItem>
</rsp:responsePack>"""

    parser = PohodaXMLParser()
    response = parser.parse_response(xml)

    assert response.raw_xml is not None
    assert "TEST" in response.raw_xml
    assert "responsePackItem" in response.raw_xml


# ============================================================================
# HTTP Client Tests
# ============================================================================


@pytest.mark.asyncio
async def test_client_send_xml_success():
    """Test successful XML send and response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"<response>OK</response>"

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = PohodaClient(
            base_url="http://test.local",
            ico="12345678",
        )

        xml_data = b'<?xml version="1.0" encoding="Windows-1250"?><test/>'
        result = await client.send_xml(xml_data)

        assert result == b"<response>OK</response>"
        mock_client.post.assert_called_once()

        # Verify headers
        call_kwargs = mock_client.post.call_args.kwargs
        assert "Content-Type" in call_kwargs["headers"]
        assert "Windows-1250" in call_kwargs["headers"]["Content-Type"]

        await client.close()


@pytest.mark.asyncio
async def test_client_http_error():
    """Test client raises PohodaResponseError on HTTP error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        client = PohodaClient(
            base_url="http://test.local",
            ico="12345678",
        )

        with pytest.raises(PohodaResponseError) as exc_info:
            await client.send_xml(b"<test/>")

        assert exc_info.value.status_code == 500
        await client.close()


@pytest.mark.asyncio
async def test_client_connection_retry():
    """Test client retries on connection error."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        # Fail twice, then succeed
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<success/>"

        mock_client.post = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.ConnectError("Connection refused"),
                mock_response,
            ]
        )
        mock_client_class.return_value = mock_client

        client = PohodaClient(
            base_url="http://test.local",
            ico="12345678",
            max_retries=3,
        )

        # Should succeed after retries
        with patch("asyncio.sleep"):  # Speed up test
            result = await client.send_xml(b"<test/>")

        assert result == b"<success/>"
        assert mock_client.post.call_count == 3
        await client.close()


@pytest.mark.asyncio
async def test_client_connection_failure_exhausted():
    """Test client raises PohodaConnectionError after max retries."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client_class.return_value = mock_client

        client = PohodaClient(
            base_url="http://test.local",
            ico="12345678",
            max_retries=2,
        )

        with pytest.raises(PohodaConnectionError) as exc_info:
            with patch("asyncio.sleep"):  # Speed up test
                await client.send_xml(b"<test/>")

        assert "after 2 attempts" in str(exc_info.value)
        await client.close()


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client works as async context manager."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200, content=b"<ok/>"))
        mock_client_class.return_value = mock_client

        async with PohodaClient(
            base_url="http://test.local",
            ico="12345678",
        ) as client:
            # Actually use the client to trigger initialization
            await client.send_xml(b"<test/>")

        # Verify close was called
        mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_client_timeout_handling():
    """Test client retries on timeout."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<ok/>"

        mock_client.post = AsyncMock(
            side_effect=[
                httpx.TimeoutException("Request timeout"),
                mock_response,
            ]
        )
        mock_client_class.return_value = mock_client

        client = PohodaClient(
            base_url="http://test.local",
            ico="12345678",
            max_retries=3,
        )

        with patch("asyncio.sleep"):
            result = await client.send_xml(b"<test/>")

        assert result == b"<ok/>"
        assert mock_client.post.call_count == 2
        await client.close()
