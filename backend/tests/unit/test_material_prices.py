"""Tests for material price management."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MaterialPrice
from app.schemas import MaterialPriceCreate, MaterialPriceUpdate
from app.services.material_price import MaterialPriceService


@pytest.fixture
async def material_price_service(test_db: AsyncSession) -> MaterialPriceService:
    """Fixture for MaterialPriceService."""
    return MaterialPriceService(test_db)


@pytest.fixture
async def sample_material_price(
    test_db: AsyncSession,
    material_price_service: MaterialPriceService,
) -> MaterialPrice:
    """Fixture for a sample material price."""
    data = MaterialPriceCreate(
        name="Ocel S235JR",
        specification="EN 10025-2, tloušťka 10mm",
        material_grade="S235JR",
        form="plech",
        dimension="10x1000x2000mm",
        unit="kg",
        unit_price=Decimal("32.50"),
        supplier="Ferona",
        valid_from=date.today() - timedelta(days=30),
        valid_to=date.today() + timedelta(days=365),
        is_active=True,
        notes="Běžná konstrukční ocel",
    )
    price = await material_price_service.create(data)
    await test_db.commit()
    return price


class TestMaterialPriceService:
    """Tests for MaterialPriceService."""

    async def test_create_material_price(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test creating a new material price."""
        data = MaterialPriceCreate(
            name="Nerezová ocel 304",
            specification="EN 10088-2",
            material_grade="1.4301",
            form="trubka",
            dimension="DN100",
            unit="m",
            unit_price=Decimal("1250.00"),
            supplier="ArcelorMittal",
            valid_from=date.today(),
            valid_to=None,  # Indefinite
            is_active=True,
            notes=None,
        )

        price = await material_price_service.create(data)
        await test_db.commit()

        assert price.id is not None
        assert price.name == "Nerezová ocel 304"
        assert price.material_grade == "1.4301"
        assert price.unit_price == Decimal("1250.00")
        assert price.supplier == "ArcelorMittal"
        assert price.is_active is True
        assert price.valid_to is None

    async def test_get_by_id(
        self,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test retrieving material price by ID."""
        price = await material_price_service.get_by_id(sample_material_price.id)

        assert price is not None
        assert price.id == sample_material_price.id
        assert price.name == "Ocel S235JR"

    async def test_get_by_id_not_found(
        self,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test retrieving non-existent material price."""
        price = await material_price_service.get_by_id(uuid.uuid4())

        assert price is None

    async def test_get_all(
        self,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test retrieving all material prices."""
        items, total = await material_price_service.get_all()

        assert total >= 1
        assert len(items) >= 1
        assert any(item.id == sample_material_price.id for item in items)

    async def test_get_all_with_search(
        self,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test searching material prices by name."""
        items, total = await material_price_service.get_all(search="S235")

        assert total >= 1
        assert all("S235" in item.name or "S235" in (item.specification or "") for item in items)

    async def test_get_all_with_material_grade_filter(
        self,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test filtering by material grade."""
        items, total = await material_price_service.get_all(material_grade="S235JR")

        assert total >= 1
        assert all(item.material_grade == "S235JR" for item in items)

    async def test_get_all_with_form_filter(
        self,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test filtering by form."""
        items, total = await material_price_service.get_all(form="plech")

        assert total >= 1
        assert all(item.form == "plech" for item in items)

    async def test_get_all_with_is_active_filter(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test filtering by active status."""
        # Create inactive price
        data = MaterialPriceCreate(
            name="Neaktivní materiál",
            material_grade="OLD",
            unit="kg",
            unit_price=Decimal("10.00"),
            valid_from=date.today(),
            is_active=False,
        )
        await material_price_service.create(data)
        await test_db.commit()

        # Get only active
        items, total = await material_price_service.get_all(is_active=True)
        assert all(item.is_active for item in items)

        # Get only inactive
        items, total = await material_price_service.get_all(is_active=False)
        assert all(not item.is_active for item in items)

    async def test_get_all_pagination(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test pagination."""
        # Create multiple prices
        for i in range(5):
            data = MaterialPriceCreate(
                name=f"Test Material {i}",
                material_grade=f"TEST{i}",
                unit="kg",
                unit_price=Decimal(f"{i * 10}.00"),
                valid_from=date.today(),
            )
            await material_price_service.create(data)
        await test_db.commit()

        # Get first page
        items, total = await material_price_service.get_all(skip=0, limit=2)
        assert len(items) == 2
        assert total >= 5

        # Get second page
        items, total = await material_price_service.get_all(skip=2, limit=2)
        assert len(items) >= 2

    async def test_update(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test updating material price."""
        update_data = MaterialPriceUpdate(
            unit_price=Decimal("35.00"),
            supplier="Updated Supplier",
            notes="Aktualizováno",
        )

        updated = await material_price_service.update(sample_material_price.id, update_data)
        await test_db.commit()

        assert updated is not None
        assert updated.unit_price == Decimal("35.00")
        assert updated.supplier == "Updated Supplier"
        assert updated.notes == "Aktualizováno"
        # Unchanged fields remain the same
        assert updated.name == "Ocel S235JR"
        assert updated.material_grade == "S235JR"

    async def test_update_not_found(
        self,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test updating non-existent material price."""
        update_data = MaterialPriceUpdate(unit_price=Decimal("100.00"))
        updated = await material_price_service.update(uuid.uuid4(), update_data)

        assert updated is None

    async def test_delete(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
        sample_material_price: MaterialPrice,
    ) -> None:
        """Test deleting material price."""
        price_id = sample_material_price.id
        success = await material_price_service.delete(price_id)
        await test_db.commit()

        assert success is True

        # Verify deletion
        deleted = await material_price_service.get_by_id(price_id)
        assert deleted is None

    async def test_delete_not_found(
        self,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test deleting non-existent material price."""
        success = await material_price_service.delete(uuid.uuid4())

        assert success is False

    async def test_find_best_price_by_grade(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test finding best price by material grade."""
        # Create multiple prices for same grade
        for i in range(3):
            data = MaterialPriceCreate(
                name=f"S235JR Variant {i}",
                material_grade="S235JR",
                unit="kg",
                unit_price=Decimal(f"{30 + i * 5}.00"),  # 30, 35, 40
                valid_from=date.today(),
                is_active=True,
            )
            await material_price_service.create(data)
        await test_db.commit()

        # Find best (cheapest) price
        best = await material_price_service.find_best_price(material_grade="S235JR")

        assert best is not None
        assert best.material_grade == "S235JR"
        assert best.unit_price == Decimal("30.00")  # Cheapest

    async def test_find_best_price_by_name(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test finding best price by name LIKE match."""
        data = MaterialPriceCreate(
            name="Nerezová tyč 12mm",
            material_grade="1.4301",
            unit="m",
            unit_price=Decimal("250.00"),
            valid_from=date.today(),
            is_active=True,
        )
        await material_price_service.create(data)
        await test_db.commit()

        # Find by partial name
        best = await material_price_service.find_best_price(material_name="Nerezová")

        assert best is not None
        assert "Nerezová" in best.name
        assert best.unit_price == Decimal("250.00")

    async def test_find_best_price_not_found(
        self,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test finding best price when no match exists."""
        best = await material_price_service.find_best_price(
            material_name="NonExistent", material_grade="FAKE123"
        )

        assert best is None

    async def test_find_best_price_validity_filter(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test that expired prices are not returned."""
        # Create expired price
        data = MaterialPriceCreate(
            name="Expired Material",
            material_grade="EXP",
            unit="kg",
            unit_price=Decimal("10.00"),
            valid_from=date.today() - timedelta(days=365),
            valid_to=date.today() - timedelta(days=1),  # Expired yesterday
            is_active=True,
        )
        await material_price_service.create(data)
        await test_db.commit()

        # Should not find expired price
        best = await material_price_service.find_best_price(material_grade="EXP")

        assert best is None

    async def test_find_best_price_inactive_filter(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test that inactive prices are not returned."""
        # Create inactive price
        data = MaterialPriceCreate(
            name="Inactive Material",
            material_grade="INACT",
            unit="kg",
            unit_price=Decimal("5.00"),
            valid_from=date.today(),
            is_active=False,  # Inactive
        )
        await material_price_service.create(data)
        await test_db.commit()

        # Should not find inactive price
        best = await material_price_service.find_best_price(material_grade="INACT")

        assert best is None

    async def test_find_best_price_future_validity(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test that future-valid prices are not returned."""
        # Create future price
        data = MaterialPriceCreate(
            name="Future Material",
            material_grade="FUT",
            unit="kg",
            unit_price=Decimal("100.00"),
            valid_from=date.today() + timedelta(days=30),  # Valid in future
            is_active=True,
        )
        await material_price_service.create(data)
        await test_db.commit()

        # Should not find future price
        best = await material_price_service.find_best_price(material_grade="FUT")

        assert best is None

    async def test_import_from_excel(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test importing material prices from Excel."""
        # Create a minimal Excel file
        from io import BytesIO

        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        assert ws is not None

        # Header row
        ws.append(
            [
                "name",
                "material_grade",
                "unit",
                "unit_price",
                "supplier",
                "valid_from",
                "is_active",
            ]
        )

        # Data rows
        ws.append(["Ocel S235", "S235JR", "kg", 32.5, "Ferona", date.today(), True])
        ws.append(["Nerez 304", "1.4301", "kg", 120.0, "ArcelorMittal", date.today(), True])

        # Save to BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        # Import
        result = await material_price_service.import_from_excel(excel_file.read())
        await test_db.commit()

        assert result.success is True
        assert result.imported_count == 2
        assert result.failed_count == 0
        assert len(result.errors) == 0

        # Verify imported data
        items, total = await material_price_service.get_all(search="S235")
        assert any(item.name == "Ocel S235" for item in items)

    async def test_import_from_excel_with_errors(
        self,
        test_db: AsyncSession,
        material_price_service: MaterialPriceService,
    ) -> None:
        """Test Excel import with some invalid rows."""
        from io import BytesIO

        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        assert ws is not None

        # Header row
        ws.append(["name", "unit", "unit_price", "valid_from"])

        # Valid row
        ws.append(["Valid Material", "kg", 50.0, date.today()])

        # Invalid row (missing required field 'name')
        ws.append([None, "kg", 100.0, date.today()])

        # Invalid row (negative price)
        ws.append(["Negative Price", "kg", -10.0, date.today()])

        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        result = await material_price_service.import_from_excel(excel_file.read())
        await test_db.commit()

        # Should partially succeed
        assert result.imported_count >= 1
        assert result.failed_count >= 1
        assert len(result.errors) >= 1
