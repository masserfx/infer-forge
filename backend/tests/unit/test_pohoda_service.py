"""Tests for Pohoda service and HTTP client."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from lxml import etree

from app.integrations.pohoda.client import PohodaClient
from app.integrations.pohoda.exceptions import (
    PohodaConnectionError,
    PohodaResponseError,
)
from app.integrations.pohoda.xml_parser import (
    PohodaResponse,
    PohodaResponseItem,
)
from app.models.pohoda_sync import PohodaSyncLog, SyncDirection, SyncStatus


# --- HTTP Client Tests ---


class TestPohodaClient:
    """Tests for Pohoda HTTP client."""

    @pytest.fixture
    def client(self) -> PohodaClient:
        """Create client instance."""
        return PohodaClient(
            base_url="http://test-server:8080",
            ico="04856562",
            timeout=5.0,
            max_retries=2,
        )

    @pytest.mark.asyncio
    async def test_send_xml_success(self, client: PohodaClient) -> None:
        """Successful XML send should return response bytes."""
        response_xml = b'<?xml version="1.0"?><response>ok</response>'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = response_xml

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            result = await client.send_xml(b"<test/>")

        assert result == response_xml
        mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_xml_http_error(self, client: PohodaClient) -> None:
        """HTTP error should raise PohodaResponseError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            with pytest.raises(PohodaResponseError) as exc_info:
                await client.send_xml(b"<test/>")

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_send_xml_correct_headers(self, client: PohodaClient) -> None:
        """Request should use Windows-1250 content type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<ok/>"

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            await client.send_xml(b"<test/>")

        call_kwargs = mock_http.post.call_args
        assert "Windows-1250" in call_kwargs.kwargs["headers"]["Content-Type"]

    @pytest.mark.asyncio
    async def test_send_xml_correct_endpoint(self, client: PohodaClient) -> None:
        """Request should be sent to /xml endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<ok/>"

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_get.return_value = mock_http

            await client.send_xml(b"<test/>")

        call_args = mock_http.post.call_args
        assert call_args.args[0] == "http://test-server:8080/xml"

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Client should work as async context manager."""
        async with PohodaClient("http://test:8080", "12345678") as client:
            assert client is not None

    def test_base_url_trailing_slash_stripped(self) -> None:
        """Trailing slash should be stripped from base URL."""
        client = PohodaClient("http://test:8080/", "12345678")
        assert client.base_url == "http://test:8080"


# --- PohodaSyncLog Model Tests ---


class TestPohodaSyncLogModel:
    """Tests for PohodaSyncLog model."""

    def test_sync_direction_values(self) -> None:
        """SyncDirection enum should have export and import values."""
        assert SyncDirection.EXPORT.value == "export"
        assert SyncDirection.IMPORT.value == "import"

    def test_sync_status_values(self) -> None:
        """SyncStatus enum should have pending, success, error values."""
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.SUCCESS.value == "success"
        assert SyncStatus.ERROR.value == "error"


# --- Pohoda Service Tests ---


class TestPohodaService:
    """Tests for Pohoda service (sync logic)."""

    @pytest.mark.asyncio
    async def test_sync_customer_not_found(self, test_db) -> None:
        """Syncing non-existent customer should raise ValueError."""
        from app.services.pohoda import PohodaService

        service = PohodaService(test_db)
        with pytest.raises(ValueError, match="not found"):
            await service.sync_customer(uuid4())

    @pytest.mark.asyncio
    async def test_sync_order_not_found(self, test_db) -> None:
        """Syncing non-existent order should raise ValueError."""
        from app.services.pohoda import PohodaService

        service = PohodaService(test_db)
        with pytest.raises(ValueError, match="not found"):
            await service.sync_order(uuid4())

    @pytest.mark.asyncio
    async def test_sync_offer_not_found(self, test_db) -> None:
        """Syncing non-existent offer should raise ValueError."""
        from app.services.pohoda import PohodaService

        service = PohodaService(test_db)
        with pytest.raises(ValueError, match="not found"):
            await service.sync_offer(uuid4())

    @pytest.mark.asyncio
    async def test_sync_customer_no_mserver(self, test_db) -> None:
        """Customer sync without mServer URL should succeed (dry run)."""
        from app.models import Customer
        from app.services.pohoda import PohodaService

        # Create test customer
        customer = Customer(
            company_name="Test s.r.o.",
            ico="99887766",
            contact_name="Test Person",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()
        await test_db.refresh(customer)

        service = PohodaService(test_db)

        with patch("app.services.pohoda.settings") as mock_settings:
            mock_settings.POHODA_MSERVER_URL = ""
            mock_settings.POHODA_ICO = "04856562"
            sync_log = await service.sync_customer(customer.id)

        assert sync_log.status == SyncStatus.SUCCESS
        assert sync_log.entity_type == "customer"
        assert sync_log.direction == SyncDirection.EXPORT

    @pytest.mark.asyncio
    async def test_sync_customer_creates_audit_log(self, test_db) -> None:
        """Customer sync should create audit log entry."""
        from sqlalchemy import select

        from app.models import AuditLog, Customer
        from app.services.pohoda import PohodaService

        customer = Customer(
            company_name="Audit Test s.r.o.",
            ico="11223344",
            contact_name="Audit Person",
            email="audit@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()
        await test_db.refresh(customer)

        service = PohodaService(test_db)

        with patch("app.services.pohoda.settings") as mock_settings:
            mock_settings.POHODA_MSERVER_URL = ""
            mock_settings.POHODA_ICO = "04856562"
            await service.sync_customer(customer.id)

        # Check audit log was created
        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "customer",
                AuditLog.entity_id == customer.id,
            )
        )
        audit = result.scalar_one_or_none()
        assert audit is not None
        assert "pohoda_sync" in audit.changes

    @pytest.mark.asyncio
    async def test_get_sync_status_empty(self, test_db) -> None:
        """Sync status for entity with no syncs should return empty."""
        from app.services.pohoda import PohodaService

        service = PohodaService(test_db)
        entity_id = uuid4()
        status = await service.get_sync_status("customer", entity_id)

        assert status["entity_type"] == "customer"
        assert status["entity_id"] == entity_id
        assert status["last_sync"] is None
        assert status["sync_count"] == 0

    @pytest.mark.asyncio
    async def test_get_sync_logs_empty(self, test_db) -> None:
        """Get sync logs should return empty list when no logs exist."""
        from app.services.pohoda import PohodaService

        service = PohodaService(test_db)
        logs = await service.get_sync_logs()
        assert logs == []

    @pytest.mark.asyncio
    async def test_sync_customer_with_mserver_success(self, test_db) -> None:
        """Customer sync with successful mServer response."""
        from app.models import Customer
        from app.services.pohoda import PohodaService

        customer = Customer(
            company_name="mServer Test s.r.o.",
            ico="55667788",
            contact_name="mServer Person",
            email="mserver@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()
        await test_db.refresh(customer)

        # Mock successful mServer response
        mock_response = PohodaResponse(
            pack_id="001",
            success=True,
            items=[PohodaResponseItem(id="999", state="ok", note="Created")],
            raw_xml="<ok/>",
        )

        service = PohodaService(test_db)

        with (
            patch("app.services.pohoda.settings") as mock_settings,
            patch("app.integrations.pohoda.client.PohodaClient") as MockClient,
            patch(
                "app.integrations.pohoda.xml_parser.PohodaXMLParser.parse_response",
                return_value=mock_response,
            ),
        ):
            mock_settings.POHODA_MSERVER_URL = "http://test:8080"
            mock_settings.POHODA_ICO = "04856562"

            # Mock client context manager
            mock_client_instance = AsyncMock()
            mock_client_instance.send_xml.return_value = b"<response/>"
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client_instance

            sync_log = await service.sync_customer(customer.id)

        assert sync_log.status == SyncStatus.SUCCESS
        assert sync_log.pohoda_doc_number == "999"
