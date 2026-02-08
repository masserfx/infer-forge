"""Tests for production protocol generation (dimensional and material certificates)."""

import sys
from datetime import date
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest

from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderPriority, OrderStatus
from app.services.document_generator import DocumentGeneratorService


@pytest.fixture(autouse=True)
def mock_weasyprint(monkeypatch):
    """Mock WeasyPrint for all tests in this module."""
    mock_html_class = MagicMock()
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.return_value = b"PDF_CONTENT_DIMENSIONAL_PROTOCOL"
    mock_html_class.return_value = mock_html_instance

    mock_weasyprint = Mock()
    mock_weasyprint.HTML = mock_html_class

    sys.modules["weasyprint"] = mock_weasyprint
    yield
    if "weasyprint" in sys.modules:
        del sys.modules["weasyprint"]


@pytest.fixture
async def sample_order_with_items(test_db):
    """Create a sample order with customer and items for testing."""
    customer = Customer(
        company_name="Test Strojírna s.r.o.",
        ico="12345678",
        dic="CZ12345678",
        contact_name="Jan Novák",
        email="jan.novak@test.cz",
        phone="+420 123 456 789",
        address="Testovací 123, 741 01 Nový Jičín",
    )
    test_db.add(customer)
    await test_db.flush()

    order = Order(
        number="Z-2026-001",
        customer_id=customer.id,
        status=OrderStatus.VYROBA,
        priority=OrderPriority.NORMAL,
        note="Testovací zakázka pro protokoly",
    )
    test_db.add(order)
    await test_db.flush()

    items = [
        OrderItem(
            order_id=order.id,
            name="Kolenový díl 90°",
            material="P235GH",
            dn="DN200",
            pn="PN16",
            quantity=5,
            unit="ks",
        ),
        OrderItem(
            order_id=order.id,
            name="T-kus redukovaný",
            material="P265GH",
            dn="DN150",
            pn="PN25",
            quantity=3,
            unit="ks",
        ),
        OrderItem(
            order_id=order.id,
            name="Příruba plochá",
            material="S235JR",
            dn="DN100",
            pn="PN40",
            quantity=10,
            unit="ks",
        ),
    ]
    for item in items:
        test_db.add(item)

    await test_db.commit()
    await test_db.refresh(order)

    return order


@pytest.mark.asyncio
async def test_generate_dimensional_protocol_success(test_db, sample_order_with_items):
    """Test successful generation of dimensional protocol PDF."""
    service = DocumentGeneratorService(test_db)

    pdf_bytes = await service.generate_dimensional_protocol(
        order_id=sample_order_with_items.id
    )

    assert pdf_bytes == b"PDF_CONTENT_DIMENSIONAL_PROTOCOL"
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


@pytest.mark.asyncio
async def test_generate_dimensional_protocol_order_not_found(test_db):
    """Test dimensional protocol generation with non-existent order."""
    service = DocumentGeneratorService(test_db)
    non_existent_id = uuid4()

    with pytest.raises(ValueError, match=f"Zakázka {non_existent_id} nenalezena"):
        await service.generate_dimensional_protocol(order_id=non_existent_id)


@pytest.mark.asyncio
async def test_generate_material_certificate_31(test_db, sample_order_with_items):
    """Test successful generation of material certificate type 3.1."""
    service = DocumentGeneratorService(test_db)

    pdf_bytes = await service.generate_material_certificate(
        order_id=sample_order_with_items.id,
        certificate_type="3.1",
    )

    assert pdf_bytes == b"PDF_CONTENT_DIMENSIONAL_PROTOCOL"
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


@pytest.mark.asyncio
async def test_generate_material_certificate_32(test_db, sample_order_with_items):
    """Test successful generation of material certificate type 3.2."""
    service = DocumentGeneratorService(test_db)

    pdf_bytes = await service.generate_material_certificate(
        order_id=sample_order_with_items.id,
        certificate_type="3.2",
    )

    assert pdf_bytes == b"PDF_CONTENT_DIMENSIONAL_PROTOCOL"
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


@pytest.mark.asyncio
async def test_generate_material_certificate_invalid_type(test_db, sample_order_with_items):
    """Test material certificate generation with invalid certificate type."""
    service = DocumentGeneratorService(test_db)

    with pytest.raises(ValueError, match="Neplatný typ atestu: 2.2"):
        await service.generate_material_certificate(
            order_id=sample_order_with_items.id,
            certificate_type="2.2",
        )


@pytest.mark.asyncio
async def test_generate_material_certificate_order_not_found(test_db):
    """Test material certificate generation with non-existent order."""
    service = DocumentGeneratorService(test_db)
    non_existent_id = uuid4()

    with pytest.raises(ValueError, match=f"Zakázka {non_existent_id} nenalezena"):
        await service.generate_material_certificate(
            order_id=non_existent_id,
            certificate_type="3.1",
        )


@pytest.mark.asyncio
async def test_dimensional_protocol_includes_items(test_db, sample_order_with_items, monkeypatch):
    """Test that dimensional protocol HTML contains item data."""
    service = DocumentGeneratorService(test_db)

    # Capture rendered HTML content
    rendered_html = None

    import sys

    def capture_html(string=None, **kwargs):
        nonlocal rendered_html
        rendered_html = string
        instance = MagicMock()
        instance.write_pdf.return_value = b"PDF_CONTENT_WITH_ITEMS"
        return instance

    monkeypatch.setattr(sys.modules["weasyprint"], "HTML", capture_html)

    await service.generate_dimensional_protocol(order_id=sample_order_with_items.id)

    assert rendered_html is not None
    assert "Rozměrový protokol" in rendered_html
    assert sample_order_with_items.number in rendered_html
    assert "Kolenový díl 90°" in rendered_html
    assert "P235GH" in rendered_html
    assert "DN200" in rendered_html
    assert "T-kus redukovaný" in rendered_html
    assert "Příruba plochá" in rendered_html

    # Protocol number format check
    today = date.today()
    expected_protocol_prefix = f"RP-{today.strftime('%Y%m%d')}"
    assert expected_protocol_prefix in rendered_html


@pytest.mark.asyncio
async def test_material_certificate_includes_material(test_db, sample_order_with_items, monkeypatch):
    """Test that material certificate HTML contains material and item data."""
    service = DocumentGeneratorService(test_db)

    # Capture rendered HTML content
    rendered_html = None

    def capture_html(string=None, **kwargs):
        nonlocal rendered_html
        rendered_html = string
        instance = MagicMock()
        instance.write_pdf.return_value = b"PDF_CONTENT_WITH_MATERIALS"
        return instance

    monkeypatch.setattr(sys.modules["weasyprint"], "HTML", capture_html)

    await service.generate_material_certificate(
        order_id=sample_order_with_items.id,
        certificate_type="3.1",
    )

    assert rendered_html is not None
    assert "Materiálový atest" in rendered_html
    assert "EN 10-204" in rendered_html
    assert "Typ 3.1" in rendered_html
    assert sample_order_with_items.number in rendered_html
    assert "Test Strojírna s.r.o." in rendered_html
    assert "Kolenový díl 90°" in rendered_html
    assert "P235GH" in rendered_html
    assert "P265GH" in rendered_html
    assert "S235JR" in rendered_html

    # Certificate number format check
    today = date.today()
    expected_cert_prefix = f"MA-31-{today.strftime('%Y%m%d')}"
    assert expected_cert_prefix in rendered_html


@pytest.mark.asyncio
async def test_material_certificate_type_32_includes_correct_badge(test_db, sample_order_with_items, monkeypatch):
    """Test that material certificate type 3.2 displays correct type badge."""
    service = DocumentGeneratorService(test_db)

    rendered_html = None

    def capture_html(string=None, **kwargs):
        nonlocal rendered_html
        rendered_html = string
        instance = MagicMock()
        instance.write_pdf.return_value = b"PDF_CONTENT_TYPE_32"
        return instance

    monkeypatch.setattr(sys.modules["weasyprint"], "HTML", capture_html)

    await service.generate_material_certificate(
        order_id=sample_order_with_items.id,
        certificate_type="3.2",
    )

    assert rendered_html is not None
    assert "Typ 3.2" in rendered_html
    assert "nezávislého na výrobě" in rendered_html  # 3.2 specific text

    # Certificate number format check for type 3.2
    today = date.today()
    expected_cert_prefix = f"MA-32-{today.strftime('%Y%m%d')}"
    assert expected_cert_prefix in rendered_html
