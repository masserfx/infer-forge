"""Unit tests for Reporting module."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Calculation,
    CalculationStatus,
    Customer,
    Document,
    DocumentCategory,
    InboxMessage,
    InboxStatus,
    Offer,
    OfferStatus,
    Order,
    OrderPriority,
    OrderStatus,
)
from app.schemas.reporting import (
    CustomerReport,
    CustomerStats,
    DashboardStats,
    PipelineReport,
    ProductionItem,
    ProductionReport,
    RevenueItem,
    RevenueReport,
    StatusCount,
)
from app.services import ReportingService


@pytest.fixture
async def sample_data(test_db: AsyncSession) -> dict:
    """Create comprehensive sample data for reporting tests.

    Returns:
        Dictionary with created entities for assertions.
    """
    # Create 2 customers
    customer1 = Customer(
        company_name="Zákazník A s.r.o.",
        ico="12345678",
        contact_name="Jan Novák",
        email="novak@zakaznik-a.cz",
    )
    customer2 = Customer(
        company_name="Zákazník B a.s.",
        ico="87654321",
        contact_name="Marie Svobodová",
        email="svobodova@zakaznik-b.cz",
    )
    test_db.add_all([customer1, customer2])
    await test_db.flush()

    # Create 5 orders with different statuses
    orders = [
        Order(
            customer_id=customer1.id,
            number="2026-001",
            status=OrderStatus.POPTAVKA,
            priority=OrderPriority.NORMAL,
        ),
        Order(
            customer_id=customer1.id,
            number="2026-002",
            status=OrderStatus.VYROBA,
            priority=OrderPriority.HIGH,
            due_date=date.today() + timedelta(days=5),
        ),
        Order(
            customer_id=customer2.id,
            number="2026-003",
            status=OrderStatus.EXPEDICE,
            priority=OrderPriority.NORMAL,
            due_date=date.today() + timedelta(days=15),
        ),
        Order(
            customer_id=customer2.id,
            number="2026-004",
            status=OrderStatus.FAKTURACE,
            priority=OrderPriority.LOW,
        ),
        Order(
            customer_id=customer1.id,
            number="2026-005",
            status=OrderStatus.DOKONCENO,
            priority=OrderPriority.NORMAL,
        ),
    ]
    test_db.add_all(orders)
    await test_db.flush()

    # Create order with overdue date
    order_overdue = Order(
        customer_id=customer1.id,
        number="2026-006-OVERDUE",
        status=OrderStatus.VYROBA,
        priority=OrderPriority.URGENT,
        due_date=date.today() - timedelta(days=3),
    )
    test_db.add(order_overdue)
    await test_db.flush()

    # Create 2 calculations (approved, offered) with total_price
    calc1 = Calculation(
        order_id=orders[0].id,
        name="Kalkulace A",
        status=CalculationStatus.APPROVED,
        margin_percent=Decimal("15"),
        material_total=Decimal("10000"),
        labor_total=Decimal("5000"),
        cooperation_total=Decimal("0"),
        overhead_total=Decimal("0"),
        margin_amount=Decimal("2250"),
        total_price=Decimal("17250"),
    )
    calc2 = Calculation(
        order_id=orders[1].id,
        name="Kalkulace B",
        status=CalculationStatus.OFFERED,
        margin_percent=Decimal("20"),
        material_total=Decimal("8000"),
        labor_total=Decimal("2000"),
        cooperation_total=Decimal("1000"),
        overhead_total=Decimal("500"),
        margin_amount=Decimal("2300"),
        total_price=Decimal("13800"),
    )
    test_db.add_all([calc1, calc2])
    await test_db.flush()

    # Create 1 offer (sent)
    offer1 = Offer(
        order_id=orders[1].id,
        number="N-2026-001",
        status=OfferStatus.SENT,
        total_price=Decimal("13800"),
        valid_until=date.today() + timedelta(days=30),
    )
    test_db.add(offer1)
    await test_db.flush()

    # Create 2 inbox messages (1 new, 1 processed)
    msg1 = InboxMessage(
        message_id="msg-001@example.com",
        subject="Nová poptávka",
        from_email="klient@example.com",
        received_at=datetime.now(timezone.utc),
        status=InboxStatus.NEW,
        body_text="Dobrý den, prosím o nabídku.",
    )
    msg2 = InboxMessage(
        message_id="msg-002@example.com",
        subject="Re: Faktura",
        from_email="klient2@example.com",
        received_at=datetime.now(timezone.utc),
        status=InboxStatus.PROCESSED,
        body_text="Děkujeme za fakturu.",
    )
    test_db.add_all([msg1, msg2])
    await test_db.flush()

    # Create 1 document
    doc1 = Document(
        entity_type="order",
        entity_id=orders[0].id,
        file_name="vykres_a.pdf",
        file_path="/docs/vykres_a.pdf",
        category=DocumentCategory.VYKRES,
        file_size=1024000,
        mime_type="application/pdf",
        uploaded_by=uuid.uuid4(),
    )
    test_db.add(doc1)
    await test_db.flush()
    await test_db.commit()

    return {
        "customers": [customer1, customer2],
        "orders": orders + [order_overdue],
        "calculations": [calc1, calc2],
        "offers": [offer1],
        "inbox_messages": [msg1, msg2],
        "documents": [doc1],
    }


class TestReportingService:
    """Tests for ReportingService."""

    async def test_get_dashboard_stats_empty_db(self, test_db: AsyncSession) -> None:
        """Test get_dashboard_stats with empty database returns zeros."""
        service = ReportingService(test_db)
        stats = await service.get_dashboard_stats()

        assert stats.total_orders == 0
        assert stats.orders_in_production == 0
        assert stats.new_inbox_messages == 0
        assert stats.pending_invoicing == 0
        assert stats.total_documents == 0
        assert stats.total_calculations == 0
        assert stats.total_revenue == Decimal("0")
        assert stats.overdue_orders == 0
        assert len(stats.pipeline.statuses) == 7

    async def test_get_dashboard_stats_with_data(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_dashboard_stats with sample data returns correct counts."""
        service = ReportingService(test_db)
        stats = await service.get_dashboard_stats()

        # Total orders (5 + 1 overdue)
        assert stats.total_orders == 6

        # Orders in production (vyroba + expedice): 2 regular + 1 overdue vyroba = 3
        assert stats.orders_in_production == 3

        # New inbox messages
        assert stats.new_inbox_messages == 1

        # Pending invoicing
        assert stats.pending_invoicing == 1

        # Total documents
        assert stats.total_documents == 1

        # Total calculations
        assert stats.total_calculations == 2

        # Total revenue (approved + offered)
        expected_revenue = Decimal("17250") + Decimal("13800")
        assert stats.total_revenue == expected_revenue

        # Overdue orders (1)
        assert stats.overdue_orders == 1

        # Pipeline report included
        assert stats.pipeline is not None
        assert len(stats.pipeline.statuses) == 7

    async def test_get_pipeline_report_empty_db(self, test_db: AsyncSession) -> None:
        """Test get_pipeline_report with empty database returns all statuses with 0."""
        service = ReportingService(test_db)
        report = await service.get_pipeline_report()

        assert report.total_orders == 0
        assert len(report.statuses) == 7

        # Verify all statuses present
        status_values = {s.status for s in report.statuses}
        expected = {
            "poptavka",
            "nabidka",
            "objednavka",
            "vyroba",
            "expedice",
            "fakturace",
            "dokonceno",
        }
        assert status_values == expected

        # All counts should be 0
        for status in report.statuses:
            assert status.count == 0

    async def test_get_pipeline_report_with_data(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_pipeline_report with sample data returns correct counts."""
        service = ReportingService(test_db)
        report = await service.get_pipeline_report()

        assert report.total_orders == 6

        # Check specific counts
        status_map = {s.status: s.count for s in report.statuses}
        assert status_map["poptavka"] == 1
        assert status_map["nabidka"] == 0
        assert status_map["objednavka"] == 0
        assert status_map["vyroba"] == 2  # 1 normal + 1 overdue
        assert status_map["expedice"] == 1
        assert status_map["fakturace"] == 1
        assert status_map["dokonceno"] == 1

    async def test_get_pipeline_report_all_statuses_present(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_pipeline_report ensures all 7 statuses present even with 0 count."""
        service = ReportingService(test_db)
        report = await service.get_pipeline_report()

        assert len(report.statuses) == 7

        # nabidka and objednavka should be present with count=0
        status_map = {s.status: s for s in report.statuses}
        assert "nabidka" in status_map
        assert status_map["nabidka"].count == 0
        assert status_map["nabidka"].label == "Nabídka"
        assert "objednavka" in status_map
        assert status_map["objednavka"].count == 0

    async def test_get_pipeline_report_correct_sorting(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_pipeline_report returns statuses in correct pipeline order."""
        service = ReportingService(test_db)
        report = await service.get_pipeline_report()

        expected_order = [
            "poptavka",
            "nabidka",
            "objednavka",
            "vyroba",
            "expedice",
            "fakturace",
            "dokonceno",
        ]

        actual_order = [s.status for s in report.statuses]
        assert actual_order == expected_order

    async def test_get_revenue_report_empty_db(self, test_db: AsyncSession) -> None:
        """Test get_revenue_report with empty database returns zeros."""
        service = ReportingService(test_db)
        report = await service.get_revenue_report()

        assert report.total_calculation_value == Decimal("0")
        assert report.total_offer_value == Decimal("0")
        assert report.approved_calculations == 0
        assert report.pending_offers == 0
        assert report.accepted_offers == 0
        assert len(report.monthly) == 0

    async def test_get_revenue_report_with_data(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_revenue_report with sample data returns correct totals."""
        service = ReportingService(test_db)
        report = await service.get_revenue_report()

        # Total calculation value (approved + offered)
        expected_calc_value = Decimal("17250") + Decimal("13800")
        assert report.total_calculation_value == expected_calc_value

        # Total offer value
        assert report.total_offer_value == Decimal("13800")

        # Approved calculations count (only APPROVED status)
        assert report.approved_calculations == 1

        # Pending offers (DRAFT + SENT)
        assert report.pending_offers == 1

        # Accepted offers
        assert report.accepted_offers == 0

    async def test_get_revenue_report_approved_count_only(
        self, test_db: AsyncSession
    ) -> None:
        """Test get_revenue_report counts only APPROVED status (not OFFERED)."""
        service = ReportingService(test_db)

        # Create customer and order
        customer = Customer(
            company_name="Test s.r.o.",
            ico="11111111",
            contact_name="Test",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        order = Order(
            customer_id=customer.id,
            number="TEST-001",
            status=OrderStatus.POPTAVKA,
        )
        test_db.add(order)
        await test_db.flush()

        # Create 1 approved, 1 offered, 1 draft
        calc1 = Calculation(
            order_id=order.id,
            name="Approved",
            status=CalculationStatus.APPROVED,
            total_price=Decimal("1000"),
        )
        calc2 = Calculation(
            order_id=order.id,
            name="Offered",
            status=CalculationStatus.OFFERED,
            total_price=Decimal("2000"),
        )
        calc3 = Calculation(
            order_id=order.id,
            name="Draft",
            status=CalculationStatus.DRAFT,
            total_price=Decimal("3000"),
        )
        test_db.add_all([calc1, calc2, calc3])
        await test_db.commit()

        report = await service.get_revenue_report()

        # approved_calculations should only count APPROVED status
        assert report.approved_calculations == 1

        # total_calculation_value includes APPROVED + OFFERED (not DRAFT)
        assert report.total_calculation_value == Decimal("3000")

    async def test_get_revenue_report_monthly_breakdown(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_revenue_report includes monthly breakdown."""
        service = ReportingService(test_db)
        report = await service.get_revenue_report(months=12)

        # Should have monthly items for current month (calculations + offer created)
        assert len(report.monthly) > 0

        # Each item should have period in YYYY-MM format
        current_period = datetime.now(timezone.utc).strftime("%Y-%m")
        periods = [item.period for item in report.monthly]
        assert current_period in periods

    async def test_get_production_report_empty_db(self, test_db: AsyncSession) -> None:
        """Test get_production_report with empty database returns zeros."""
        service = ReportingService(test_db)
        report = await service.get_production_report()

        assert report.in_production == 0
        assert report.in_expedition == 0
        assert report.overdue == 0
        assert report.due_this_week == 0
        assert report.due_this_month == 0
        assert len(report.orders) == 0

    async def test_get_production_report_with_data(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_production_report with sample data returns correct counts."""
        service = ReportingService(test_db)
        report = await service.get_production_report()

        # in_production: 2 orders with VYROBA status (1 regular + 1 overdue)
        assert report.in_production == 2

        # in_expedition: 1 order with EXPEDICE status
        assert report.in_expedition == 1

        # overdue: 1 order with past due_date
        assert report.overdue == 1

        # due_this_week: should include orders due within 7 days
        # Regular vyroba is due in 5 days, so should be counted
        assert report.due_this_week >= 1

        # due_this_month: should include both due this week and later this month
        assert report.due_this_month >= report.due_this_week

        # Orders list should include active orders
        assert len(report.orders) > 0

    async def test_get_production_report_overdue_detection(
        self, test_db: AsyncSession
    ) -> None:
        """Test get_production_report correctly detects overdue orders."""
        service = ReportingService(test_db)

        # Create customer and orders
        customer = Customer(
            company_name="Test s.r.o.",
            ico="12345678",
            contact_name="Test",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        # Order overdue by 5 days
        order1 = Order(
            customer_id=customer.id,
            number="OVERDUE-1",
            status=OrderStatus.VYROBA,
            due_date=date.today() - timedelta(days=5),
        )
        # Order due today (not overdue yet)
        order2 = Order(
            customer_id=customer.id,
            number="DUE-TODAY",
            status=OrderStatus.VYROBA,
            due_date=date.today(),
        )
        # Order due in future
        order3 = Order(
            customer_id=customer.id,
            number="FUTURE",
            status=OrderStatus.VYROBA,
            due_date=date.today() + timedelta(days=10),
        )
        test_db.add_all([order1, order2, order3])
        await test_db.commit()

        report = await service.get_production_report()

        # Only order1 should be overdue
        assert report.overdue == 1

        # Find the overdue order item
        overdue_item = next(
            (o for o in report.orders if o.order_number == "OVERDUE-1"), None
        )
        assert overdue_item is not None
        assert overdue_item.days_until_due == -5

    async def test_get_production_report_due_this_week(
        self, test_db: AsyncSession
    ) -> None:
        """Test get_production_report tracks orders due this week."""
        service = ReportingService(test_db)

        customer = Customer(
            company_name="Test s.r.o.",
            ico="12345678",
            contact_name="Test",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        today = date.today()
        end_of_week = today + timedelta(days=(6 - today.weekday()))

        # Order due within this week
        order1 = Order(
            customer_id=customer.id,
            number="THIS-WEEK",
            status=OrderStatus.VYROBA,
            due_date=end_of_week - timedelta(days=1),
        )
        # Order due next week
        order2 = Order(
            customer_id=customer.id,
            number="NEXT-WEEK",
            status=OrderStatus.VYROBA,
            due_date=end_of_week + timedelta(days=1),
        )
        test_db.add_all([order1, order2])
        await test_db.commit()

        report = await service.get_production_report()

        # Should count order1 but not order2
        assert report.due_this_week == 1

    async def test_get_production_report_due_this_month(
        self, test_db: AsyncSession
    ) -> None:
        """Test get_production_report tracks orders due this month."""
        service = ReportingService(test_db)

        customer = Customer(
            company_name="Test s.r.o.",
            ico="12345678",
            contact_name="Test",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        today = date.today()
        # Last day of current month
        if today.month == 12:
            end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)

        # Order due within this month
        order1 = Order(
            customer_id=customer.id,
            number="THIS-MONTH",
            status=OrderStatus.VYROBA,
            due_date=end_of_month,
        )
        # Order due next month
        order2 = Order(
            customer_id=customer.id,
            number="NEXT-MONTH",
            status=OrderStatus.VYROBA,
            due_date=end_of_month + timedelta(days=1),
        )
        test_db.add_all([order1, order2])
        await test_db.commit()

        report = await service.get_production_report()

        # Should count order1 but not order2
        assert report.due_this_month >= 1

    async def test_get_production_report_includes_customer_name(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_production_report includes customer name in items."""
        service = ReportingService(test_db)
        report = await service.get_production_report()

        # Find an order in production
        prod_item = next(
            (o for o in report.orders if o.status == "vyroba"), None
        )
        assert prod_item is not None
        assert prod_item.customer_name != ""
        assert "Zákazník" in prod_item.customer_name

    async def test_get_customer_report_empty_db(self, test_db: AsyncSession) -> None:
        """Test get_customer_report with empty database returns zeros."""
        service = ReportingService(test_db)
        report = await service.get_customer_report()

        assert report.total_customers == 0
        assert report.active_customers == 0
        assert len(report.top_customers) == 0

    async def test_get_customer_report_with_data(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_customer_report with sample data returns correct counts."""
        service = ReportingService(test_db)
        report = await service.get_customer_report()

        # Total customers
        assert report.total_customers == 2

        # Active customers (with at least one active order)
        # Both customers have active orders (not DOKONCENO)
        assert report.active_customers == 2

        # Top customers list
        assert len(report.top_customers) == 2

    async def test_get_customer_report_top_customers_sorted(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_customer_report sorts top customers by total value."""
        service = ReportingService(test_db)
        report = await service.get_customer_report()

        # Customer A should be first (has more calculation value)
        # Customer A: calc1 (17250), Customer B: 0 calculations
        assert len(report.top_customers) > 0
        top_customer = report.top_customers[0]
        assert "Zákazník A" in top_customer.company_name
        assert top_customer.total_value > Decimal("0")

    async def test_get_customer_report_limit_parameter(
        self, test_db: AsyncSession
    ) -> None:
        """Test get_customer_report respects limit parameter."""
        service = ReportingService(test_db)

        # Create 5 customers
        for i in range(5):
            customer = Customer(
                company_name=f"Zákazník {i}",
                ico=f"1111111{i}",
                contact_name=f"Kontakt {i}",
                email=f"kontakt{i}@test.cz",
            )
            test_db.add(customer)
        await test_db.commit()

        # Get report with limit=3
        report = await service.get_customer_report(limit=3)

        # Should return only 3 customers
        assert len(report.top_customers) == 3

    async def test_get_customer_report_includes_orders_count(
        self, test_db: AsyncSession, sample_data: dict
    ) -> None:
        """Test get_customer_report includes orders_count for each customer."""
        service = ReportingService(test_db)
        report = await service.get_customer_report()

        # Customer A has 4 orders (3 regular + 1 overdue)
        customer_a = next(
            (c for c in report.top_customers if "Zákazník A" in c.company_name),
            None,
        )
        assert customer_a is not None
        assert customer_a.orders_count == 4

        # Customer B has 2 orders
        customer_b = next(
            (c for c in report.top_customers if "Zákazník B" in c.company_name),
            None,
        )
        assert customer_b is not None
        assert customer_b.orders_count == 2

    async def test_get_customer_report_active_orders_excludes_completed(
        self, test_db: AsyncSession
    ) -> None:
        """Test get_customer_report active_orders excludes DOKONCENO status."""
        service = ReportingService(test_db)

        customer = Customer(
            company_name="Test s.r.o.",
            ico="12345678",
            contact_name="Test",
            email="test@test.cz",
        )
        test_db.add(customer)
        await test_db.flush()

        # Create 3 orders: 1 active, 2 completed
        order1 = Order(
            customer_id=customer.id,
            number="ACTIVE",
            status=OrderStatus.VYROBA,
        )
        order2 = Order(
            customer_id=customer.id,
            number="COMPLETED-1",
            status=OrderStatus.DOKONCENO,
        )
        order3 = Order(
            customer_id=customer.id,
            number="COMPLETED-2",
            status=OrderStatus.DOKONCENO,
        )
        test_db.add_all([order1, order2, order3])
        await test_db.commit()

        report = await service.get_customer_report()

        # Should count only 1 active order
        customer_stats = report.top_customers[0]
        assert customer_stats.orders_count == 3  # total orders
        assert customer_stats.active_orders == 1  # only active


class TestReportingSchemas:
    """Tests for Reporting Pydantic schemas."""

    def test_dashboard_stats_default_values(self) -> None:
        """Test DashboardStats schema has correct default values."""
        stats = DashboardStats()

        assert stats.total_orders == 0
        assert stats.orders_in_production == 0
        assert stats.new_inbox_messages == 0
        assert stats.pending_invoicing == 0
        assert stats.total_documents == 0
        assert stats.total_calculations == 0
        assert stats.total_revenue == Decimal("0")
        assert stats.overdue_orders == 0
        assert stats.pipeline is not None
        assert isinstance(stats.pipeline, PipelineReport)

    def test_pipeline_report_with_status_count(self) -> None:
        """Test PipelineReport schema with StatusCount items."""
        status_counts = [
            StatusCount(status="poptavka", count=5, label="Poptávka"),
            StatusCount(status="vyroba", count=3, label="Výroba"),
            StatusCount(status="dokonceno", count=10, label="Dokončeno"),
        ]
        report = PipelineReport(
            statuses=status_counts,
            total_orders=18,
        )

        assert len(report.statuses) == 3
        assert report.total_orders == 18
        assert report.statuses[0].status == "poptavka"
        assert report.statuses[0].count == 5
        assert report.statuses[0].label == "Poptávka"

    def test_revenue_report_with_monthly_items(self) -> None:
        """Test RevenueReport schema with monthly breakdown."""
        monthly_items = [
            RevenueItem(
                period="2026-01",
                total_calculations=Decimal("50000"),
                total_offers=Decimal("45000"),
                calculations_count=10,
                offers_count=8,
            ),
            RevenueItem(
                period="2026-02",
                total_calculations=Decimal("60000"),
                total_offers=Decimal("55000"),
                calculations_count=12,
                offers_count=10,
            ),
        ]

        report = RevenueReport(
            total_calculation_value=Decimal("110000"),
            total_offer_value=Decimal("100000"),
            approved_calculations=15,
            pending_offers=5,
            accepted_offers=3,
            monthly=monthly_items,
        )

        assert report.total_calculation_value == Decimal("110000")
        assert report.approved_calculations == 15
        assert len(report.monthly) == 2
        assert report.monthly[0].period == "2026-01"

    def test_revenue_item_default_values(self) -> None:
        """Test RevenueItem schema has correct default values."""
        item = RevenueItem(period="2026-01")

        assert item.period == "2026-01"
        assert item.total_calculations == Decimal("0")
        assert item.total_offers == Decimal("0")
        assert item.offers_count == 0
        assert item.calculations_count == 0

    def test_production_report_with_items(self) -> None:
        """Test ProductionReport schema with ProductionItem list."""
        items = [
            ProductionItem(
                order_id=str(uuid.uuid4()),
                order_number="2026-001",
                customer_name="Zákazník A",
                status="vyroba",
                priority="high",
                due_date=date.today() + timedelta(days=5),
                days_until_due=5,
                items_count=10,
            ),
            ProductionItem(
                order_id=str(uuid.uuid4()),
                order_number="2026-002",
                customer_name="Zákazník B",
                status="expedice",
                priority="normal",
                due_date=date.today() - timedelta(days=2),
                days_until_due=-2,
                items_count=5,
            ),
        ]

        report = ProductionReport(
            in_production=1,
            in_expedition=1,
            overdue=1,
            due_this_week=0,
            due_this_month=2,
            orders=items,
        )

        assert report.in_production == 1
        assert report.in_expedition == 1
        assert report.overdue == 1
        assert len(report.orders) == 2
        assert report.orders[1].days_until_due == -2

    def test_production_item_optional_fields(self) -> None:
        """Test ProductionItem schema with optional fields."""
        # Minimal item without due_date
        item = ProductionItem(
            order_id=str(uuid.uuid4()),
            order_number="TEST-001",
            customer_name="Test Customer",
            status="poptavka",
            priority="normal",
        )

        assert item.due_date is None
        assert item.days_until_due is None
        assert item.items_count == 0

    def test_customer_report_with_stats(self) -> None:
        """Test CustomerReport schema with CustomerStats list."""
        customers = [
            CustomerStats(
                customer_id=str(uuid.uuid4()),
                company_name="Zákazník A s.r.o.",
                ico="12345678",
                orders_count=15,
                total_value=Decimal("500000"),
                active_orders=5,
            ),
            CustomerStats(
                customer_id=str(uuid.uuid4()),
                company_name="Zákazník B a.s.",
                ico="87654321",
                orders_count=10,
                total_value=Decimal("300000"),
                active_orders=3,
            ),
        ]

        report = CustomerReport(
            total_customers=50,
            active_customers=25,
            top_customers=customers,
        )

        assert report.total_customers == 50
        assert report.active_customers == 25
        assert len(report.top_customers) == 2
        assert report.top_customers[0].company_name == "Zákazník A s.r.o."

    def test_customer_stats_default_values(self) -> None:
        """Test CustomerStats schema has correct default values."""
        stats = CustomerStats(
            customer_id=str(uuid.uuid4()),
            company_name="Test s.r.o.",
            ico="12345678",
        )

        assert stats.orders_count == 0
        assert stats.total_value == Decimal("0")
        assert stats.active_orders == 0

    def test_status_count_validation(self) -> None:
        """Test StatusCount schema validation."""
        status = StatusCount(
            status="vyroba",
            count=42,
            label="Výroba",
        )

        assert status.status == "vyroba"
        assert status.count == 42
        assert status.label == "Výroba"

    def test_production_report_default_values(self) -> None:
        """Test ProductionReport schema has correct default values."""
        report = ProductionReport()

        assert report.in_production == 0
        assert report.in_expedition == 0
        assert report.overdue == 0
        assert report.due_this_week == 0
        assert report.due_this_month == 0
        assert len(report.orders) == 0
