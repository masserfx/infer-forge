"""Unit tests for embedding service."""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderPriority, OrderStatus
from app.services.embedding import (
    EmbeddingService,
    compute_content_hash,
    extract_order_text,
)


@pytest.fixture
async def sample_order(test_db: AsyncSession) -> Order:
    """Create a sample order with items for testing."""
    customer = Customer(
        company_name="Test Steel s.r.o.",
        ico="12345678",
        contact_name="Jan Novak",
        email="jan@test-steel.cz",
    )
    test_db.add(customer)
    await test_db.flush()

    order = Order(
        customer_id=customer.id,
        number="ZK-2024-001",
        status=OrderStatus.NABIDKA,
        priority=OrderPriority.HIGH,
        note="Urgentní zakázka na potrubní díly",
    )
    test_db.add(order)
    await test_db.flush()

    item1 = OrderItem(
        order_id=order.id,
        name="Koleno 90°",
        material="P265GH",
        quantity=Decimal("10"),
        unit="ks",
        dn="150",
        pn="16",
        note="Dle výkresu V-001",
    )
    item2 = OrderItem(
        order_id=order.id,
        name="Příruba plochá",
        material="11 353",
        quantity=Decimal("20"),
        unit="ks",
        dn="200",
        pn="10",
    )
    test_db.add_all([item1, item2])
    await test_db.flush()

    # Refresh to load relationships
    await test_db.refresh(order, ["items"])
    return order


class TestExtractOrderText:
    """Tests for extract_order_text function."""

    async def test_basic_extraction(self, sample_order: Order) -> None:
        """Test text extraction from order."""
        text = extract_order_text(sample_order)

        assert "ZK-2024-001" in text
        assert "nabidka" in text
        assert "high" in text
        assert "Urgentní zakázka" in text
        assert "Koleno 90°" in text
        assert "P265GH" in text
        assert "DN150" in text
        assert "PN16" in text
        assert "Příruba plochá" in text

    async def test_extraction_without_items(self, test_db: AsyncSession) -> None:
        """Test text extraction when order has no items."""
        customer = Customer(
            company_name="Test",
            ico="99999999",
            contact_name="Test",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="ZK-2024-002",
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.NORMAL,
        )
        test_db.add(order)
        await test_db.flush()
        await test_db.refresh(order, ["items"])

        text = extract_order_text(order)
        assert "ZK-2024-002" in text
        assert "poptavka" in text

    async def test_extraction_without_note(self, test_db: AsyncSession) -> None:
        """Test text extraction when order has no note."""
        customer = Customer(
            company_name="Test",
            ico="88888888",
            contact_name="Test",
            email="test2@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="ZK-2024-003",
            status=OrderStatus.VYROBA,
            priority=OrderPriority.URGENT,
            note=None,
        )
        test_db.add(order)
        await test_db.flush()
        await test_db.refresh(order, ["items"])

        text = extract_order_text(order)
        assert "Poznámka" not in text
        assert "ZK-2024-003" in text


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_same_text_same_hash(self) -> None:
        """Test that same text produces same hash."""
        text = "Zakázka ZK-001"
        hash1 = compute_content_hash(text)
        hash2 = compute_content_hash(text)
        assert hash1 == hash2

    def test_different_text_different_hash(self) -> None:
        """Test that different text produces different hash."""
        hash1 = compute_content_hash("Zakázka ZK-001")
        hash2 = compute_content_hash("Zakázka ZK-002")
        assert hash1 != hash2

    def test_hash_length(self) -> None:
        """Test SHA256 hash length."""
        h = compute_content_hash("test")
        assert len(h) == 64  # SHA256 hex digest

    def test_unicode_hashing(self) -> None:
        """Test hashing of Czech characters."""
        h = compute_content_hash("Příruba plochá DN200 PN10")
        assert len(h) == 64
        # Should be deterministic
        h2 = compute_content_hash("Příruba plochá DN200 PN10")
        assert h == h2


class TestEmbeddingServiceGenerate:
    """Tests for EmbeddingService.generate_embedding."""

    @patch("app.services.embedding._get_model")
    async def test_generate_embedding_creates_new(
        self, mock_get_model: MagicMock, test_db: AsyncSession, sample_order: Order
    ) -> None:
        """Test generating a new embedding."""
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
        mock_get_model.return_value = mock_model

        service = EmbeddingService(test_db)
        embedding = await service.generate_embedding(sample_order.id)

        assert embedding is not None
        assert embedding.order_id == sample_order.id
        assert embedding.content_hash is not None
        assert len(embedding.content_hash) == 64
        assert "ZK-2024-001" in embedding.text_content

    @patch("app.services.embedding._get_model")
    async def test_generate_embedding_skips_unchanged(
        self, mock_get_model: MagicMock, test_db: AsyncSession, sample_order: Order
    ) -> None:
        """Test that unchanged content doesn't regenerate embedding."""
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
        mock_get_model.return_value = mock_model

        service = EmbeddingService(test_db)

        # Generate first time
        embedding1 = await service.generate_embedding(sample_order.id)
        assert embedding1 is not None

        # Generate again — should skip (same hash)
        embedding2 = await service.generate_embedding(sample_order.id)
        assert embedding2 is not None
        assert embedding2.id == embedding1.id
        # Model.encode should only be called once
        assert mock_model.encode.call_count == 1

    @patch("app.services.embedding._get_model")
    async def test_generate_embedding_order_not_found(
        self, mock_get_model: MagicMock, test_db: AsyncSession
    ) -> None:
        """Test generating embedding for non-existent order."""
        service = EmbeddingService(test_db)
        result = await service.generate_embedding(uuid.uuid4())
        assert result is None

    @patch("app.services.embedding._get_model")
    async def test_generate_embedding_updates_changed(
        self, mock_get_model: MagicMock, test_db: AsyncSession, sample_order: Order
    ) -> None:
        """Test that changed content regenerates embedding."""
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
        mock_get_model.return_value = mock_model

        service = EmbeddingService(test_db)

        # Generate first time
        embedding1 = await service.generate_embedding(sample_order.id)
        assert embedding1 is not None
        old_hash = embedding1.content_hash

        # Modify the order
        sample_order.note = "Změněná poznámka"
        await test_db.flush()
        await test_db.refresh(sample_order, ["items"])

        # Generate again — should update
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.2] * 384)
        embedding2 = await service.generate_embedding(sample_order.id)
        assert embedding2 is not None
        assert embedding2.content_hash != old_hash
        assert mock_model.encode.call_count == 2
