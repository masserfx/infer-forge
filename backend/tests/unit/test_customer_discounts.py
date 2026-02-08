"""Tests for customer discount and category system."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog, Customer, Order, OrderStatus
from app.schemas import (
    CalculationCreate,
    CalculationItemCreate,
    CustomerCreate,
    CustomerUpdate,
)
from app.services import CalculationService, CustomerService


@pytest.fixture
async def test_customer(test_db: AsyncSession) -> Customer:
    """Create a test customer."""
    customer = Customer(
        company_name="Test Company s.r.o.",
        ico="12345678",
        contact_name="Jan Novák",
        email="test@example.com",
    )
    test_db.add(customer)
    await test_db.flush()
    await test_db.refresh(customer)
    return customer


@pytest.fixture
async def test_order(test_db: AsyncSession, test_customer: Customer) -> Order:
    """Create a test order."""
    order = Order(
        customer_id=test_customer.id,
        number="2024-001",
        status=OrderStatus.POPTAVKA,
    )
    test_db.add(order)
    await test_db.flush()
    await test_db.refresh(order)
    return order


@pytest.fixture
def test_user_id() -> uuid.UUID:
    """Return a test user ID."""
    return uuid.uuid4()


class TestCustomerCategories:
    """Test customer category and discount system."""

    @pytest.mark.asyncio
    async def test_create_customer_with_category(
        self,
        test_db: AsyncSession,
    ) -> None:
        """Test creating customer with category."""
        service = CustomerService(test_db)

        customer_data = CustomerCreate(
            company_name="Test Category Company",
            ico="12345678",
            contact_name="Jan Novák",
            email="jan@test.cz",
            category="A",
            discount_percent=Decimal("15.00"),
            payment_terms_days=30,
        )

        customer = await service.create(customer_data)
        await test_db.commit()

        assert customer.category == "A"
        assert customer.discount_percent == Decimal("15.00")
        assert customer.payment_terms_days == 30

    @pytest.mark.asyncio
    async def test_default_category_values(
        self,
        test_db: AsyncSession,
    ) -> None:
        """Test that default category is C with 0% discount."""
        service = CustomerService(test_db)

        customer_data = CustomerCreate(
            company_name="Default Category Company",
            ico="87654321",
            contact_name="Petr Svoboda",
            email="petr@test.cz",
        )

        customer = await service.create(customer_data)
        await test_db.commit()

        assert customer.category == "C"
        assert customer.discount_percent == Decimal("0.00")
        assert customer.payment_terms_days == 14

    @pytest.mark.asyncio
    async def test_update_customer_category(
        self,
        test_db: AsyncSession,
        test_customer: Customer,
    ) -> None:
        """Test updating customer category via update method."""
        service = CustomerService(test_db)

        update_data = CustomerUpdate(
            category="A",
            discount_percent=Decimal("10.00"),
            payment_terms_days=30,
        )

        updated = await service.update(test_customer.id, update_data)
        await test_db.commit()

        assert updated is not None
        assert updated.category == "A"
        assert updated.discount_percent == Decimal("10.00")
        assert updated.payment_terms_days == 30

    @pytest.mark.asyncio
    async def test_update_category_with_defaults(
        self,
        test_db: AsyncSession,
        test_customer: Customer,
        test_user_id: str,
    ) -> None:
        """Test update_category method applies default discount/payment terms."""
        service = CustomerService(test_db, user_id=test_user_id)

        # Upgrade to category A
        updated = await service.update_category(test_customer.id, "A")
        await test_db.commit()

        assert updated is not None
        assert updated.category == "A"
        assert updated.discount_percent == Decimal("15.00")
        assert updated.payment_terms_days == 30

        # Downgrade to category B
        updated = await service.update_category(test_customer.id, "B")
        await test_db.commit()

        assert updated.category == "B"
        assert updated.discount_percent == Decimal("5.00")
        assert updated.payment_terms_days == 14

        # Downgrade to category C
        updated = await service.update_category(test_customer.id, "C")
        await test_db.commit()

        assert updated.category == "C"
        assert updated.discount_percent == Decimal("0.00")
        assert updated.payment_terms_days == 7

    @pytest.mark.asyncio
    async def test_update_category_audit_trail(
        self,
        test_db: AsyncSession,
        test_customer: Customer,
        test_user_id: str,
    ) -> None:
        """Test that category updates create audit log entries."""
        from sqlalchemy import select

        service = CustomerService(test_db, user_id=test_user_id)

        await service.update_category(test_customer.id, "A")
        await test_db.commit()

        # Check audit log
        result = await test_db.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == "customer")
            .where(AuditLog.entity_id == test_customer.id)
            .where(AuditLog.action == AuditAction.UPDATE)
        )
        audit = result.scalar_one()

        assert audit.user_id == test_user_id
        assert "category" in audit.changes
        assert audit.changes["category"]["new"] == "A"
        assert "discount_percent" in audit.changes
        assert "payment_terms_days" in audit.changes

    @pytest.mark.asyncio
    async def test_invalid_category_validation(
        self,
        test_db: AsyncSession,
    ) -> None:
        """Test that invalid category is rejected by schema validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(
                company_name="Invalid Category",
                ico="11111111",
                contact_name="Test",
                email="test@test.cz",
                category="X",  # Invalid
            )

        assert "Category must be A, B, or C" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_discount_percent(
        self,
        test_db: AsyncSession,
    ) -> None:
        """Test that discount outside 0-100 range is rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CustomerCreate(
                company_name="Invalid Discount",
                ico="22222222",
                contact_name="Test",
                email="test@test.cz",
                discount_percent=Decimal("150.00"),  # > 100
            )

        with pytest.raises(ValidationError):
            CustomerCreate(
                company_name="Invalid Discount",
                ico="33333333",
                contact_name="Test",
                email="test@test.cz",
                discount_percent=Decimal("-5.00"),  # < 0
            )


class TestCalculationWithDiscount:
    """Test calculation service with customer discount."""

    @pytest.mark.asyncio
    async def test_calculation_without_customer_discount(
        self,
        test_db: AsyncSession,
        test_order: Order,
        test_user_id: str,
    ) -> None:
        """Test calculation when customer has no discount (category C)."""
        # Ensure customer has no discount
        test_order.customer.category = "C"
        test_order.customer.discount_percent = Decimal("0.00")
        await test_db.commit()

        service = CalculationService(test_db, user_id=test_user_id)

        calc_data = CalculationCreate(
            order_id=test_order.id,
            name="Test Calc No Discount",
            margin_percent=Decimal("20.00"),
            items=[
                CalculationItemCreate(
                    cost_type="material",
                    name="Steel",
                    quantity=Decimal("10"),
                    unit="kg",
                    unit_price=Decimal("100.00"),
                )
            ],
        )

        calc = await service.create(calc_data)
        await test_db.commit()

        # Material: 10 * 100 = 1000
        # Margin: 1000 * 20% = 200
        # Total: 1200 (no discount)
        assert calc.material_total == Decimal("1000.00")
        assert calc.margin_amount == Decimal("200.00")
        assert calc.total_price == Decimal("1200.00")

    @pytest.mark.asyncio
    async def test_calculation_with_customer_discount_category_a(
        self,
        test_db: AsyncSession,
        test_order: Order,
        test_user_id: str,
    ) -> None:
        """Test calculation applies 15% customer discount for category A."""
        # Set customer to category A
        test_order.customer.category = "A"
        test_order.customer.discount_percent = Decimal("15.00")
        await test_db.commit()

        service = CalculationService(test_db, user_id=test_user_id)

        calc_data = CalculationCreate(
            order_id=test_order.id,
            name="Test Calc With Discount A",
            margin_percent=Decimal("20.00"),
            items=[
                CalculationItemCreate(
                    cost_type="material",
                    name="Steel",
                    quantity=Decimal("10"),
                    unit="kg",
                    unit_price=Decimal("100.00"),
                )
            ],
        )

        calc = await service.create(calc_data)
        await test_db.commit()

        # Material: 10 * 100 = 1000
        # Margin: 1000 * 20% = 200
        # Subtotal: 1200
        # Customer discount: 1200 * 15% = 180
        # Total: 1200 - 180 = 1020
        assert calc.material_total == Decimal("1000.00")
        assert calc.margin_amount == Decimal("200.00")
        assert calc.total_price == Decimal("1020.00")

    @pytest.mark.asyncio
    async def test_calculation_with_customer_discount_category_b(
        self,
        test_db: AsyncSession,
        test_order: Order,
        test_user_id: str,
    ) -> None:
        """Test calculation applies 5% customer discount for category B."""
        # Set customer to category B
        test_order.customer.category = "B"
        test_order.customer.discount_percent = Decimal("5.00")
        await test_db.commit()

        service = CalculationService(test_db, user_id=test_user_id)

        calc_data = CalculationCreate(
            order_id=test_order.id,
            name="Test Calc With Discount B",
            margin_percent=Decimal("15.00"),
            items=[
                CalculationItemCreate(
                    cost_type="material",
                    name="Steel",
                    quantity=Decimal("20"),
                    unit="kg",
                    unit_price=Decimal("50.00"),
                )
            ],
        )

        calc = await service.create(calc_data)
        await test_db.commit()

        # Material: 20 * 50 = 1000
        # Margin: 1000 * 15% = 150
        # Subtotal: 1150
        # Customer discount: 1150 * 5% = 57.50
        # Total: 1150 - 57.50 = 1092.50
        assert calc.material_total == Decimal("1000.00")
        assert calc.margin_amount == Decimal("150.00")
        assert calc.total_price == Decimal("1092.50")

    @pytest.mark.asyncio
    async def test_calculation_discount_with_multiple_cost_types(
        self,
        test_db: AsyncSession,
        test_order: Order,
        test_user_id: str,
    ) -> None:
        """Test customer discount applies to total with multiple cost types."""
        # Set customer to category A (15% discount)
        test_order.customer.category = "A"
        test_order.customer.discount_percent = Decimal("15.00")
        await test_db.commit()

        service = CalculationService(test_db, user_id=test_user_id)

        calc_data = CalculationCreate(
            order_id=test_order.id,
            name="Test Multi-Cost Discount",
            margin_percent=Decimal("20.00"),
            items=[
                CalculationItemCreate(
                    cost_type="material",
                    name="Steel",
                    quantity=Decimal("10"),
                    unit="kg",
                    unit_price=Decimal("100.00"),
                ),
                CalculationItemCreate(
                    cost_type="labor",
                    name="Welding",
                    quantity=Decimal("8"),
                    unit="h",
                    unit_price=Decimal("50.00"),
                ),
                CalculationItemCreate(
                    cost_type="cooperation",
                    name="NDT Testing",
                    quantity=Decimal("1"),
                    unit="ks",
                    unit_price=Decimal("300.00"),
                ),
            ],
        )

        calc = await service.create(calc_data)
        await test_db.commit()

        # Material: 10 * 100 = 1000
        # Labor: 8 * 50 = 400
        # Cooperation: 1 * 300 = 300
        # Subtotal: 1700
        # Margin: 1700 * 20% = 340
        # Before discount: 2040
        # Customer discount: 2040 * 15% = 306
        # Total: 2040 - 306 = 1734
        assert calc.material_total == Decimal("1000.00")
        assert calc.labor_total == Decimal("400.00")
        assert calc.cooperation_total == Decimal("300.00")
        assert calc.margin_amount == Decimal("340.00")
        assert calc.total_price == Decimal("1734.00")

    @pytest.mark.asyncio
    async def test_calculation_recalculates_on_item_update(
        self,
        test_db: AsyncSession,
        test_order: Order,
        test_user_id: str,
    ) -> None:
        """Test that customer discount is reapplied when items are updated."""
        # Set customer to category A (15% discount)
        test_order.customer.category = "A"
        test_order.customer.discount_percent = Decimal("15.00")
        await test_db.commit()

        service = CalculationService(test_db, user_id=test_user_id)

        # Create calculation
        calc_data = CalculationCreate(
            order_id=test_order.id,
            name="Test Item Update Discount",
            margin_percent=Decimal("20.00"),
            items=[
                CalculationItemCreate(
                    cost_type="material",
                    name="Steel",
                    quantity=Decimal("10"),
                    unit="kg",
                    unit_price=Decimal("100.00"),
                )
            ],
        )

        calc = await service.create(calc_data)
        await test_db.commit()

        # Initial total: (1000 + 200) * 0.85 = 1020
        assert calc.total_price == Decimal("1020.00")

        # Add another item
        new_item = CalculationItemCreate(
            cost_type="labor",
            name="Welding",
            quantity=Decimal("5"),
            unit="h",
            unit_price=Decimal("60.00"),
        )

        calc = await service.add_item(calc.id, new_item)
        await test_db.commit()

        # New total: material 1000 + labor 300 = 1300
        # Margin: 1300 * 20% = 260
        # Before discount: 1560
        # Customer discount: 1560 * 15% = 234
        # Total: 1560 - 234 = 1326
        assert calc.material_total == Decimal("1000.00")
        assert calc.labor_total == Decimal("300.00")
        assert calc.margin_amount == Decimal("260.00")
        assert calc.total_price == Decimal("1326.00")

    @pytest.mark.asyncio
    async def test_calculation_discount_precision(
        self,
        test_db: AsyncSession,
        test_order: Order,
        test_user_id: str,
    ) -> None:
        """Test that discount calculations are precise to 2 decimal places."""
        # Set customer to category B (5% discount)
        test_order.customer.category = "B"
        test_order.customer.discount_percent = Decimal("5.00")
        await test_db.commit()

        service = CalculationService(test_db, user_id=test_user_id)

        calc_data = CalculationCreate(
            order_id=test_order.id,
            name="Test Precision",
            margin_percent=Decimal("17.50"),
            items=[
                CalculationItemCreate(
                    cost_type="material",
                    name="Steel",
                    quantity=Decimal("13.333"),
                    unit="kg",
                    unit_price=Decimal("47.89"),
                )
            ],
        )

        calc = await service.create(calc_data)
        await test_db.commit()

        # Material: 13.333 * 47.89 = 638.5193... → should be stored as Decimal
        # All calculations should be precise
        assert isinstance(calc.total_price, Decimal)
        # Verify it's rounded to 2 decimal places
        assert calc.total_price == calc.total_price.quantize(Decimal("0.01"))
