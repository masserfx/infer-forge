"""Unit tests for DeadlineMonitorService."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationType
from app.models.operation import Operation, OperationStatus
from app.models.order import Order, OrderPriority, OrderStatus
from app.services.deadline_monitor import DeadlineMonitorService


def _make_order(
    *,
    status: OrderStatus = OrderStatus.VYROBA,
    priority: OrderPriority = OrderPriority.NORMAL,
    due_date=None,
    number: str = "ORD-2026-001",
) -> Order:
    """Create a mock Order."""
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.status = status
    order.priority = priority
    order.due_date = due_date
    order.number = number
    order.note = None
    return order


def _make_operation(
    *,
    order: Order,
    name: str = "Svařování",
    sequence: int = 1,
    duration_hours: Decimal = Decimal("24"),
    status: str = OperationStatus.PLANNED.value,
    planned_start: datetime | None = None,
    planned_end: datetime | None = None,
    actual_start: datetime | None = None,
    actual_end: datetime | None = None,
) -> Operation:
    """Create a mock Operation."""
    op = MagicMock(spec=Operation)
    op.id = uuid.uuid4()
    op.order_id = order.id
    op.order = order
    op.name = name
    op.sequence = sequence
    op.duration_hours = duration_hours
    op.status = status
    op.planned_start = planned_start
    op.planned_end = planned_end
    op.actual_start = actual_start
    op.actual_end = actual_end
    op.notes = None
    return op


class TestCalculateWarningDays:
    """Tests for _calculate_warning_days."""

    def test_short_operation_normal_priority(self) -> None:
        """8h operation with NORMAL priority = 2 days."""
        order = _make_order(priority=OrderPriority.NORMAL)
        op = _make_operation(order=order, duration_hours=Decimal("8"))
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_warning_days(op, order)

        # 8h -> 1 day, * 1.5 (NORMAL) -> round(1.5) = 2
        assert result == 2

    def test_long_operation_normal_priority(self) -> None:
        """24h operation with NORMAL priority = 5 days."""
        order = _make_order(priority=OrderPriority.NORMAL)
        op = _make_operation(order=order, duration_hours=Decimal("24"))
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_warning_days(op, order)

        # 24h -> 3 days, * 1.5 -> round(4.5) = 4
        assert result == 4

    def test_long_operation_urgent_priority(self) -> None:
        """24h operation with URGENT priority = 9 days."""
        order = _make_order(priority=OrderPriority.URGENT)
        op = _make_operation(order=order, duration_hours=Decimal("24"))
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_warning_days(op, order)

        # 24h -> 3 days, * 3.0 -> 9
        assert result == 9

    def test_short_operation_high_priority(self) -> None:
        """4h operation with HIGH priority = 2 days."""
        order = _make_order(priority=OrderPriority.HIGH)
        op = _make_operation(order=order, duration_hours=Decimal("4"))
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_warning_days(op, order)

        # 4h -> 1 day, * 2.0 -> 2
        assert result == 2

    def test_short_operation_low_priority(self) -> None:
        """8h operation with LOW priority = 1 day (minimum)."""
        order = _make_order(priority=OrderPriority.LOW)
        op = _make_operation(order=order, duration_hours=Decimal("8"))
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_warning_days(op, order)

        # 8h -> 1 day, * 1.0 -> 1
        assert result == 1

    def test_no_duration_defaults_to_8h(self) -> None:
        """Operation without duration_hours defaults to 8h."""
        order = _make_order(priority=OrderPriority.NORMAL)
        op = _make_operation(order=order, duration_hours=None)
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_warning_days(op, order)

        # 8h (default) -> 1 day, * 1.5 -> round(1.5) = 2
        assert result == 2

    def test_minimum_is_one_day(self) -> None:
        """Warning days is at least 1."""
        order = _make_order(priority=OrderPriority.LOW)
        op = _make_operation(order=order, duration_hours=Decimal("1"))
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_warning_days(op, order)

        assert result >= 1


class TestCalculateDownstreamImpact:
    """Tests for _calculate_downstream_impact."""

    def test_no_downstream_operations(self) -> None:
        """No downstream operations means no impact."""
        order = _make_order(due_date=datetime.now(UTC).date() + timedelta(days=10))
        op = _make_operation(order=order, sequence=3)
        all_ops = [op]  # Only this operation
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_downstream_impact(op, all_ops, order)

        assert result["remaining_hours"] == 0
        assert result["due_date_at_risk"] is False
        assert result["estimated_delay_days"] == 0

    def test_downstream_hours_calculated(self) -> None:
        """Remaining hours from downstream ops are summed."""
        order = _make_order(due_date=datetime.now(UTC).date() + timedelta(days=30))
        op1 = _make_operation(
            order=order, sequence=1, duration_hours=Decimal("8"),
            planned_end=datetime.now(UTC) + timedelta(days=1),
        )
        op2 = _make_operation(
            order=order, sequence=2, duration_hours=Decimal("16"),
            status=OperationStatus.PLANNED.value,
        )
        op3 = _make_operation(
            order=order, sequence=3, duration_hours=Decimal("8"),
            status=OperationStatus.PLANNED.value,
        )
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_downstream_impact(op1, [op1, op2, op3], order)

        assert result["remaining_hours"] == 24.0

    def test_due_date_at_risk(self) -> None:
        """Due date at risk when remaining work exceeds available time."""
        today = datetime.now(UTC).date()
        order = _make_order(due_date=today + timedelta(days=1))
        op1 = _make_operation(
            order=order, sequence=1, duration_hours=Decimal("8"),
            planned_end=datetime.now(UTC) - timedelta(days=2),  # Already late
        )
        op2 = _make_operation(
            order=order, sequence=2, duration_hours=Decimal("40"),
            status=OperationStatus.PLANNED.value,
        )
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_downstream_impact(op1, [op1, op2], order)

        assert result["due_date_at_risk"] is True
        assert result["estimated_delay_days"] > 0

    def test_completed_downstream_ops_ignored(self) -> None:
        """Completed operations should not count toward remaining hours."""
        order = _make_order(due_date=datetime.now(UTC).date() + timedelta(days=30))
        op1 = _make_operation(
            order=order, sequence=1, duration_hours=Decimal("8"),
            planned_end=datetime.now(UTC) + timedelta(days=1),
        )
        op2 = _make_operation(
            order=order, sequence=2, duration_hours=Decimal("16"),
            status=OperationStatus.COMPLETED.value,
        )
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_downstream_impact(op1, [op1, op2], order)

        assert result["remaining_hours"] == 0

    def test_no_due_date(self) -> None:
        """Without due_date, risk is always False."""
        order = _make_order(due_date=None)
        op1 = _make_operation(
            order=order, sequence=1,
            planned_end=datetime.now(UTC) - timedelta(days=5),
        )
        op2 = _make_operation(
            order=order, sequence=2, duration_hours=Decimal("40"),
            status=OperationStatus.PLANNED.value,
        )
        service = DeadlineMonitorService(MagicMock())

        result = service._calculate_downstream_impact(op1, [op1, op2], order)

        assert result["due_date_at_risk"] is False
        assert result["estimated_delay_days"] == 0


class TestGenerateRuleBased:
    """Tests for _generate_rule_based fallback recommendations."""

    def test_critical_welding(self) -> None:
        """Critical severity for welding operation."""
        op = _make_operation(order=_make_order(), name="Svařování")
        service = DeadlineMonitorService(MagicMock())

        result = service._generate_rule_based(op, "critical")

        assert "směn" in result or "subdodávku" in result

    def test_critical_ndt(self) -> None:
        """Critical severity for NDT operation."""
        op = _make_operation(order=_make_order(), name="NDT kontrola")
        service = DeadlineMonitorService(MagicMock())

        result = service._generate_rule_based(op, "critical")

        assert "NDT" in result or "inspektora" in result

    def test_critical_material(self) -> None:
        """Critical severity for material reception."""
        op = _make_operation(order=_make_order(), name="Příjem materiálu")
        service = DeadlineMonitorService(MagicMock())

        result = service._generate_rule_based(op, "critical")

        assert "dodavatel" in result.lower() or "materiál" in result.lower()

    def test_critical_generic(self) -> None:
        """Critical severity for generic operation."""
        op = _make_operation(order=_make_order(), name="Lakování")
        service = DeadlineMonitorService(MagicMock())

        result = service._generate_rule_based(op, "critical")

        assert "termínu" in result or "kapacit" in result

    def test_warning(self) -> None:
        """Warning severity recommendation."""
        op = _make_operation(order=_make_order(), name="Ohýbání")
        service = DeadlineMonitorService(MagicMock())

        result = service._generate_rule_based(op, "warning")

        assert "vedoucí" in result.lower() or "priorit" in result.lower()

    def test_info(self) -> None:
        """Info severity recommendation."""
        op = _make_operation(order=_make_order(), name="Test")
        service = DeadlineMonitorService(MagicMock())

        result = service._generate_rule_based(op, "info")

        assert "blíží" in result or "sledujte" in result.lower()


class TestShouldNotify:
    """Tests for _should_notify deduplication."""

    async def test_first_notification_allowed(self) -> None:
        """First notification for an operation should be sent."""
        order = _make_order()
        op = _make_operation(order=order)

        mock_db = AsyncMock(spec=AsyncSession)
        # First query returns the operation
        mock_op_result = MagicMock()
        mock_op_result.scalar_one_or_none.return_value = op
        # Second query returns the order
        mock_order_result = MagicMock()
        mock_order_result.scalar_one_or_none.return_value = order
        # Third query returns no existing notification (dedup)
        mock_dedup_result = MagicMock()
        mock_dedup_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[mock_op_result, mock_order_result, mock_dedup_result]
        )

        service = DeadlineMonitorService(mock_db)
        result = await service._should_notify(op.id, "warning")

        assert result is True

    async def test_duplicate_notification_blocked(self) -> None:
        """Same severity notification within 24h should be blocked."""
        from app.models.notification import Notification

        order = _make_order()
        op = _make_operation(order=order)

        existing = MagicMock(spec=Notification)
        existing.title = f"{order.number}: {op.name} — varování"
        existing.created_at = datetime.now(UTC) - timedelta(hours=2)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_op_result = MagicMock()
        mock_op_result.scalar_one_or_none.return_value = op
        mock_order_result = MagicMock()
        mock_order_result.scalar_one_or_none.return_value = order
        mock_dedup_result = MagicMock()
        mock_dedup_result.scalar_one_or_none.return_value = existing

        mock_db.execute = AsyncMock(
            side_effect=[mock_op_result, mock_order_result, mock_dedup_result]
        )

        service = DeadlineMonitorService(mock_db)
        result = await service._should_notify(op.id, "warning")

        assert result is False

    async def test_escalation_allowed(self) -> None:
        """Higher severity notification should be allowed even within 24h."""
        from app.models.notification import Notification

        order = _make_order()
        op = _make_operation(order=order)

        # Existing is "info" level
        existing = MagicMock(spec=Notification)
        existing.title = f"{order.number}: {op.name} — informace"
        existing.created_at = datetime.now(UTC) - timedelta(hours=2)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_op_result = MagicMock()
        mock_op_result.scalar_one_or_none.return_value = op
        mock_order_result = MagicMock()
        mock_order_result.scalar_one_or_none.return_value = order
        mock_dedup_result = MagicMock()
        mock_dedup_result.scalar_one_or_none.return_value = existing

        mock_db.execute = AsyncMock(
            side_effect=[mock_op_result, mock_order_result, mock_dedup_result]
        )

        service = DeadlineMonitorService(mock_db)
        # Escalating from info to critical
        result = await service._should_notify(op.id, "critical")

        assert result is True

    async def test_operation_not_found(self) -> None:
        """If operation not found, allow notification (safety)."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = DeadlineMonitorService(mock_db)
        result = await service._should_notify(uuid.uuid4(), "critical")

        assert result is True


class TestCheckDeadlines:
    """Tests for check_deadlines main method."""

    async def test_no_operations_returns_empty(self) -> None:
        """No operations in VYROBA returns empty alerts."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = DeadlineMonitorService(mock_db)
        alerts = await service.check_deadlines()

        assert alerts == []

    @patch("app.services.deadline_monitor.NotificationService")
    async def test_critical_operation_detected(self, mock_notif_cls: MagicMock) -> None:
        """Operation past deadline triggers critical alert."""
        today = datetime.now(UTC).date()
        order = _make_order(
            due_date=today + timedelta(days=5),
            number="ORD-2026-010",
        )
        op = _make_operation(
            order=order,
            name="Svařování",
            sequence=1,
            duration_hours=Decimal("24"),
            planned_end=datetime.now(UTC) - timedelta(days=2),  # 2 days late
            status=OperationStatus.IN_PROGRESS.value,
        )

        mock_db = AsyncMock(spec=AsyncSession)

        # 1st call: main query returning operations
        mock_ops_result = MagicMock()
        mock_ops_result.scalars.return_value.all.return_value = [op]

        # 2nd call: _should_notify - op lookup
        mock_op_result = MagicMock()
        mock_op_result.scalar_one_or_none.return_value = op

        # 3rd call: _should_notify - order lookup
        mock_order_result = MagicMock()
        mock_order_result.scalar_one_or_none.return_value = order

        # 4th call: _should_notify - dedup check (no existing)
        mock_dedup_result = MagicMock()
        mock_dedup_result.scalar_one_or_none.return_value = None

        # 5th call: downstream ops query
        mock_all_ops_result = MagicMock()
        mock_all_ops_result.scalars.return_value.all.return_value = [op]

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_ops_result,
                mock_op_result,
                mock_order_result,
                mock_dedup_result,
                mock_all_ops_result,
            ]
        )

        # Mock NotificationService
        mock_notif_instance = AsyncMock()
        mock_notif_instance.create_for_roles = AsyncMock(return_value=[])
        mock_notif_cls.return_value = mock_notif_instance

        service = DeadlineMonitorService(mock_db)
        alerts = await service.check_deadlines()

        assert len(alerts) == 1
        assert alerts[0]["severity"] == "critical"
        assert alerts[0]["order_number"] == "ORD-2026-010"
        assert alerts[0]["operation_name"] == "Svařování"
        assert alerts[0]["days_remaining"] < 0

        # Verify notification was sent
        mock_notif_instance.create_for_roles.assert_awaited_once()
        call_kwargs = mock_notif_instance.create_for_roles.call_args
        assert call_kwargs.kwargs["notification_type"] == NotificationType.DEADLINE_WARNING

    @patch("app.services.deadline_monitor.NotificationService")
    async def test_operations_with_enough_time_no_alerts(
        self, mock_notif_cls: MagicMock
    ) -> None:
        """Operations with plenty of time remaining produce no alerts."""
        order = _make_order(priority=OrderPriority.LOW)
        op = _make_operation(
            order=order,
            name="Řezání",
            duration_hours=Decimal("4"),
            planned_end=datetime.now(UTC) + timedelta(days=30),  # Far future
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_ops_result = MagicMock()
        mock_ops_result.scalars.return_value.all.return_value = [op]
        mock_db.execute = AsyncMock(return_value=mock_ops_result)

        service = DeadlineMonitorService(mock_db)
        alerts = await service.check_deadlines()

        assert len(alerts) == 0

    @patch("app.services.deadline_monitor.NotificationService")
    async def test_dedup_skips_duplicate(self, mock_notif_cls: MagicMock) -> None:
        """Duplicate notification within 24h is skipped."""
        from app.models.notification import Notification

        order = _make_order(number="ORD-2026-020")
        op = _make_operation(
            order=order,
            name="NDT",
            planned_end=datetime.now(UTC) - timedelta(days=1),
        )

        # Existing notification from 1h ago
        existing = MagicMock(spec=Notification)
        existing.title = f"{order.number}: {op.name} — KRITICKÉ zpoždění"
        existing.created_at = datetime.now(UTC) - timedelta(hours=1)

        mock_db = AsyncMock(spec=AsyncSession)

        mock_ops_result = MagicMock()
        mock_ops_result.scalars.return_value.all.return_value = [op]

        mock_op_result = MagicMock()
        mock_op_result.scalar_one_or_none.return_value = op

        mock_order_result = MagicMock()
        mock_order_result.scalar_one_or_none.return_value = order

        mock_dedup_result = MagicMock()
        mock_dedup_result.scalar_one_or_none.return_value = existing

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_ops_result,
                mock_op_result,
                mock_order_result,
                mock_dedup_result,
            ]
        )

        service = DeadlineMonitorService(mock_db)
        alerts = await service.check_deadlines()

        assert len(alerts) == 0
        mock_notif_cls.return_value.create_for_roles.assert_not_called()


class TestGenerateRecommendation:
    """Tests for _generate_recommendation with Claude and fallback."""

    async def test_fallback_without_api_key(self) -> None:
        """Without API key, uses rule-based fallback."""
        order = _make_order()
        op = _make_operation(order=order, name="Svařování")
        mock_db = AsyncMock(spec=AsyncSession)

        service = DeadlineMonitorService(mock_db, api_key=None)
        result = await service._generate_recommendation(
            op, order, "critical", {"due_date_at_risk": True, "estimated_delay_days": 3}
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "směn" in result or "subdodávku" in result

    async def test_claude_error_falls_back_to_rules(self) -> None:
        """Claude API error falls back to rule-based."""
        order = _make_order()
        op = _make_operation(order=order, name="Svařování")
        mock_db = AsyncMock(spec=AsyncSession)

        service = DeadlineMonitorService(mock_db, api_key="test-key")
        # Mock Claude client to raise exception
        service._client = AsyncMock()
        service._client.messages.create = AsyncMock(side_effect=Exception("API error"))

        # Mock embedding service for similar orders
        with patch("app.services.deadline_monitor.EmbeddingService") as mock_emb:
            mock_emb_instance = AsyncMock()
            mock_emb_instance.find_similar = AsyncMock(return_value=[])
            mock_emb.return_value = mock_emb_instance

            result = await service._generate_recommendation(
                op, order, "critical",
                {"due_date_at_risk": True, "estimated_delay_days": 3},
            )

        assert isinstance(result, str)
        assert len(result) > 0
