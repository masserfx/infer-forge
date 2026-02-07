"""Reporting service for analytics and dashboards."""

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Calculation,
    CalculationStatus,
    Customer,
    Document,
    InboxMessage,
    InboxStatus,
    Offer,
    OfferStatus,
    Order,
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

logger = logging.getLogger(__name__)

ORDER_STATUS_LABELS = {
    "poptavka": "Poptávka",
    "nabidka": "Nabídka",
    "objednavka": "Objednávka",
    "vyroba": "Výroba",
    "expedice": "Expedice",
    "fakturace": "Fakturace",
    "dokonceno": "Dokončeno",
}

PRODUCTION_STATUSES = {OrderStatus.VYROBA, OrderStatus.EXPEDICE}
ACTIVE_STATUSES = {
    OrderStatus.POPTAVKA,
    OrderStatus.NABIDKA,
    OrderStatus.OBJEDNAVKA,
    OrderStatus.VYROBA,
    OrderStatus.EXPEDICE,
    OrderStatus.FAKTURACE,
}


class ReportingService:
    """Service for generating reports and analytics from aggregated data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self) -> DashboardStats:
        """Get aggregated dashboard statistics."""
        # Order counts by status
        pipeline = await self.get_pipeline_report()

        # Specific counts
        production_count = sum(
            s.count for s in pipeline.statuses if s.status in ("vyroba", "expedice")
        )
        invoicing_count = sum(s.count for s in pipeline.statuses if s.status == "fakturace")

        # Inbox new messages
        inbox_result = await self.db.execute(
            select(func.count(InboxMessage.id)).where(InboxMessage.status == InboxStatus.NEW)
        )
        new_messages = inbox_result.scalar() or 0

        # Documents count
        docs_result = await self.db.execute(select(func.count(Document.id)))
        total_documents = docs_result.scalar() or 0

        # Calculations count
        calc_result = await self.db.execute(select(func.count(Calculation.id)))
        total_calculations = calc_result.scalar() or 0

        # Total revenue (from approved/offered calculations)
        revenue_result = await self.db.execute(
            select(func.sum(Calculation.total_price)).where(
                Calculation.status.in_(
                    [
                        CalculationStatus.APPROVED,
                        CalculationStatus.OFFERED,
                    ]
                )
            )
        )
        total_revenue = revenue_result.scalar() or Decimal("0")

        # Overdue orders
        today = date.today()
        overdue_result = await self.db.execute(
            select(func.count(Order.id)).where(
                Order.due_date < today,
                Order.status.in_(list(ACTIVE_STATUSES)),
            )
        )
        overdue_orders = overdue_result.scalar() or 0

        return DashboardStats(
            total_orders=pipeline.total_orders,
            orders_in_production=production_count,
            new_inbox_messages=new_messages,
            pending_invoicing=invoicing_count,
            total_documents=total_documents,
            total_calculations=total_calculations,
            total_revenue=total_revenue,
            overdue_orders=overdue_orders,
            pipeline=pipeline,
        )

    async def get_pipeline_report(self) -> PipelineReport:
        """Get order pipeline breakdown by status."""
        result = await self.db.execute(
            select(
                Order.status,
                func.count(Order.id).label("count"),
            ).group_by(Order.status)
        )
        rows = result.all()

        statuses = []
        total = 0
        for row in rows:
            status_value = row[0].value if hasattr(row[0], "value") else str(row[0])
            count = row[1]
            total += count
            statuses.append(
                StatusCount(
                    status=status_value,
                    count=count,
                    label=ORDER_STATUS_LABELS.get(status_value, status_value),
                )
            )

        # Ensure all statuses are present
        existing = {s.status for s in statuses}
        for status_val, label in ORDER_STATUS_LABELS.items():
            if status_val not in existing:
                statuses.append(StatusCount(status=status_val, count=0, label=label))

        # Sort by pipeline order
        status_order = list(ORDER_STATUS_LABELS.keys())
        statuses.sort(
            key=lambda s: status_order.index(s.status) if s.status in status_order else 99
        )

        return PipelineReport(statuses=statuses, total_orders=total)

    async def get_revenue_report(self, months: int = 12) -> RevenueReport:
        """Get revenue report with monthly breakdown."""
        # Total values
        calc_result = await self.db.execute(
            select(func.sum(Calculation.total_price)).where(
                Calculation.status.in_(
                    [
                        CalculationStatus.APPROVED,
                        CalculationStatus.OFFERED,
                    ]
                )
            )
        )
        total_calc_value = calc_result.scalar() or Decimal("0")

        offer_result = await self.db.execute(select(func.sum(Offer.total_price)))
        total_offer_value = offer_result.scalar() or Decimal("0")

        # Counts
        approved_result = await self.db.execute(
            select(func.count(Calculation.id)).where(
                Calculation.status == CalculationStatus.APPROVED
            )
        )
        approved_calculations = approved_result.scalar() or 0

        pending_offers_result = await self.db.execute(
            select(func.count(Offer.id)).where(
                Offer.status.in_([OfferStatus.DRAFT, OfferStatus.SENT])
            )
        )
        pending_offers = pending_offers_result.scalar() or 0

        accepted_offers_result = await self.db.execute(
            select(func.count(Offer.id)).where(Offer.status == OfferStatus.ACCEPTED)
        )
        accepted_offers = accepted_offers_result.scalar() or 0

        # Monthly breakdown from calculations
        cutoff = datetime.now(UTC) - timedelta(days=months * 30)
        monthly_calc = await self.db.execute(
            select(
                func.strftime("%Y-%m", Calculation.created_at).label("period"),
                func.sum(Calculation.total_price).label("total"),
                func.count(Calculation.id).label("cnt"),
            )
            .where(Calculation.created_at >= cutoff)
            .group_by("period")
            .order_by("period")
        )

        monthly_items: dict[str, RevenueItem] = {}
        for row in monthly_calc.all():
            period = row[0]
            monthly_items[period] = RevenueItem(
                period=period,
                total_calculations=row[1] or Decimal("0"),
                calculations_count=row[2] or 0,
            )

        # Monthly offers
        monthly_offer = await self.db.execute(
            select(
                func.strftime("%Y-%m", Offer.created_at).label("period"),
                func.sum(Offer.total_price).label("total"),
                func.count(Offer.id).label("cnt"),
            )
            .where(Offer.created_at >= cutoff)
            .group_by("period")
            .order_by("period")
        )

        for row in monthly_offer.all():
            period = row[0]
            if period in monthly_items:
                monthly_items[period].total_offers = row[1] or Decimal("0")
                monthly_items[period].offers_count = row[2] or 0
            else:
                monthly_items[period] = RevenueItem(
                    period=period,
                    total_offers=row[1] or Decimal("0"),
                    offers_count=row[2] or 0,
                )

        monthly = sorted(monthly_items.values(), key=lambda x: x.period)

        return RevenueReport(
            total_calculation_value=total_calc_value,
            total_offer_value=total_offer_value,
            approved_calculations=approved_calculations,
            pending_offers=pending_offers,
            accepted_offers=accepted_offers,
            monthly=monthly,
        )

    async def get_production_report(self) -> ProductionReport:
        """Get production overview with deadline tracking."""
        today = date.today()
        end_of_week = today + timedelta(days=(6 - today.weekday()))
        end_of_month = date(
            today.year + (1 if today.month == 12 else 0),
            (today.month % 12) + 1,
            1,
        ) - timedelta(days=1)

        # Get active production orders
        result = await self.db.execute(
            select(Order)
            .where(Order.status.in_(list(ACTIVE_STATUSES)))
            .order_by(Order.due_date.asc().nullslast(), Order.priority.desc())
        )
        orders = list(result.scalars().all())

        production_items = []
        in_production = 0
        in_expedition = 0
        overdue = 0
        due_this_week = 0
        due_this_month = 0

        for order in orders:
            if order.status == OrderStatus.VYROBA:
                in_production += 1
            if order.status == OrderStatus.EXPEDICE:
                in_expedition += 1

            days_until_due = None
            if order.due_date:
                days_until_due = (order.due_date - today).days
                if days_until_due < 0:
                    overdue += 1
                if order.due_date <= end_of_week:
                    due_this_week += 1
                if order.due_date <= end_of_month:
                    due_this_month += 1

            # Get customer name
            customer_name = ""
            if order.customer_id:
                cust = await self.db.execute(
                    select(Customer.company_name).where(Customer.id == order.customer_id)
                )
                customer_name = cust.scalar() or ""

            # Count items
            from app.models import OrderItem

            items_result = await self.db.execute(
                select(func.count(OrderItem.id)).where(OrderItem.order_id == order.id)
            )
            items_count = items_result.scalar() or 0

            production_items.append(
                ProductionItem(
                    order_id=str(order.id),
                    order_number=order.number,
                    customer_name=customer_name,
                    status=order.status.value,
                    priority=order.priority.value,
                    due_date=order.due_date,
                    days_until_due=days_until_due,
                    items_count=items_count,
                )
            )

        return ProductionReport(
            in_production=in_production,
            in_expedition=in_expedition,
            overdue=overdue,
            due_this_week=due_this_week,
            due_this_month=due_this_month,
            orders=production_items,
        )

    async def get_customer_report(self, limit: int = 20) -> CustomerReport:
        """Get customer analytics with top customers by value."""
        # Total customers
        total_result = await self.db.execute(select(func.count(Customer.id)))
        total_customers = total_result.scalar() or 0

        # Active customers (with at least one active order)
        active_result = await self.db.execute(
            select(func.count(func.distinct(Order.customer_id))).where(
                Order.status.in_(list(ACTIVE_STATUSES))
            )
        )
        active_customers = active_result.scalar() or 0

        # Top customers by calculation value
        top_result = await self.db.execute(
            select(
                Customer.id,
                Customer.company_name,
                Customer.ico,
                func.count(func.distinct(Order.id)).label("orders_count"),
                func.coalesce(func.sum(Calculation.total_price), Decimal("0")).label("total_value"),
            )
            .outerjoin(Order, Order.customer_id == Customer.id)
            .outerjoin(Calculation, Calculation.order_id == Order.id)
            .group_by(Customer.id, Customer.company_name, Customer.ico)
            .order_by(func.coalesce(func.sum(Calculation.total_price), Decimal("0")).desc())
            .limit(limit)
        )

        top_customers = []
        for row in top_result.all():
            # Count active orders
            active_orders_result = await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.customer_id == row[0],
                    Order.status.in_(list(ACTIVE_STATUSES)),
                )
            )
            active_count = active_orders_result.scalar() or 0

            top_customers.append(
                CustomerStats(
                    customer_id=str(row[0]),
                    company_name=row[1],
                    ico=row[2],
                    orders_count=row[3],
                    total_value=row[4] or Decimal("0"),
                    active_orders=active_count,
                )
            )

        return CustomerReport(
            total_customers=total_customers,
            active_customers=active_customers,
            top_customers=top_customers,
        )
