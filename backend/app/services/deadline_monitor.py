"""Deadline monitoring service for production operations.

Detects at-risk deadlines, calculates severity based on operation duration
and order priority, generates AI-powered recommendations using historical
data from similar orders, and sends deduplicated notifications.
"""

import logging
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from anthropic import AsyncAnthropic
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification, NotificationType
from app.models.operation import Operation, OperationStatus
from app.models.order import Order, OrderPriority, OrderStatus
from app.models.user import UserRole
from app.services.embedding import EmbeddingService
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)

_MODEL: str = "claude-sonnet-4-20250514"
_MAX_TOKENS: int = 512
_TIMEOUT_SECONDS: float = 30.0

_SYSTEM_PROMPT: str = (
    "Jsi výrobní plánovač firmy Infer s.r.o. (potrubní díly, svařence, ocelové konstrukce).\n"
    "Na základě aktuálního stavu operace a zkušeností z podobných zakázek navrhni konkrétní opatření.\n"
    "Buď stručný (max 150 slov), konkrétní a praktický. Piš česky."
)

_PRIORITY_MULTIPLIER: dict[OrderPriority, float] = {
    OrderPriority.LOW: 1.0,
    OrderPriority.NORMAL: 1.5,
    OrderPriority.HIGH: 2.0,
    OrderPriority.URGENT: 3.0,
}

_SEVERITY_CZECH: dict[str, str] = {
    "critical": "KRITICKÉ zpoždění",
    "warning": "varování",
    "info": "informace",
}


class DeadlineMonitorService:
    """Service for monitoring production operation deadlines."""

    def __init__(self, db: AsyncSession, api_key: str | None = None):
        self.db = db
        self._client = AsyncAnthropic(api_key=api_key) if api_key else None

    async def check_deadlines(self) -> list[dict]:
        """Check all active operations for deadline risks.

        Returns:
            List of alert dicts with operation info, severity, and recommendation.
        """
        logger.info("deadline_monitor.started")

        # Load operations for orders in VYROBA with planned_end
        stmt = (
            select(Operation)
            .join(Order, Operation.order_id == Order.id)
            .where(
                and_(
                    Order.status == OrderStatus.VYROBA,
                    Operation.status.in_([
                        OperationStatus.PLANNED.value,
                        OperationStatus.IN_PROGRESS.value,
                    ]),
                    Operation.planned_end.is_not(None),
                )
            )
            .options(selectinload(Operation.order))
        )
        result = await self.db.execute(stmt)
        operations = list(result.scalars().all())

        logger.info("deadline_monitor.operations_found count=%d", len(operations))

        alerts: list[dict] = []
        today = datetime.now(UTC).date()

        for op in operations:
            order = op.order
            warning_days = self._calculate_warning_days(op, order)
            planned_end_date = op.planned_end.date() if op.planned_end else None
            if not planned_end_date:
                continue

            days_remaining = (planned_end_date - today).days

            # Determine severity
            severity: str | None = None
            if days_remaining < 0:
                severity = "critical"
            elif days_remaining <= 1:
                severity = "warning"
            elif days_remaining <= warning_days:
                severity = "info"

            if severity is None:
                continue

            # Check dedup
            should_send = await self._should_notify(op.id, severity)
            if not should_send:
                continue

            # Load all ops for downstream impact
            all_ops_stmt = (
                select(Operation)
                .where(Operation.order_id == order.id)
                .order_by(Operation.sequence)
            )
            all_ops_result = await self.db.execute(all_ops_stmt)
            all_ops = list(all_ops_result.scalars().all())

            impact = self._calculate_downstream_impact(op, all_ops, order)
            recommendation = await self._generate_recommendation(op, order, severity, impact)

            # Build notification
            severity_cz = _SEVERITY_CZECH.get(severity, severity)
            title = f"{order.number}: {op.name} — {severity_cz}"

            parts = [f"Operace \"{op.name}\" (seq. {op.sequence})"]
            if days_remaining < 0:
                parts.append(f"je {abs(days_remaining)} dní po termínu.")
            elif days_remaining == 0:
                parts.append("má termín DNES.")
            else:
                parts.append(f"má termín za {days_remaining} dní ({planned_end_date.isoformat()}).")

            if impact["due_date_at_risk"]:
                parts.append(
                    f"Ohrožen termín zakázky! Odhadované zpoždění: {impact['estimated_delay_days']} dní."
                )

            parts.append(f"\nDoporučení: {recommendation}")
            message = " ".join(parts)

            # Send notification
            notification_svc = NotificationService(self.db)
            await notification_svc.create_for_roles(
                notification_type=NotificationType.DEADLINE_WARNING,
                title=title,
                message=message,
                roles=[UserRole.VEDENI, UserRole.TECHNOLOG],
                link=f"/zakazky/{order.id}",
            )

            alerts.append({
                "order_number": order.number,
                "operation_name": op.name,
                "severity": severity,
                "days_remaining": days_remaining,
                "due_date_at_risk": impact["due_date_at_risk"],
                "recommendation": recommendation,
            })

        logger.info("deadline_monitor.completed alerts=%d", len(alerts))
        return alerts

    def _calculate_warning_days(self, operation: Operation, order: Order) -> int:
        """Calculate how many days before deadline to start warning.

        Longer operations and higher priority orders get earlier warnings.
        """
        duration_hours = float(operation.duration_hours or 8)
        duration_days = max(1, math.ceil(duration_hours / 8))
        multiplier = _PRIORITY_MULTIPLIER.get(order.priority, 1.5)
        return max(1, round(duration_days * multiplier))

    def _calculate_downstream_impact(
        self,
        operation: Operation,
        order_ops: list[Operation],
        order: Order,
    ) -> dict:
        """Calculate impact of this operation's delay on downstream operations and due_date."""
        remaining_hours = Decimal(0)
        for op in order_ops:
            if op.sequence > operation.sequence and op.status in (
                OperationStatus.PLANNED.value,
                OperationStatus.IN_PROGRESS.value,
            ):
                remaining_hours += op.duration_hours or Decimal(0)

        today = datetime.now(UTC).date()
        due_date_at_risk = False
        estimated_delay_days = 0

        if order.due_date:
            # Current operation delay
            planned_end_date = operation.planned_end.date() if operation.planned_end else today
            current_delay = max(0, (today - planned_end_date).days)

            # Remaining work days needed (8h workday)
            remaining_work_days = math.ceil(float(remaining_hours) / 8) if remaining_hours else 0

            # Earliest completion = today + remaining_work_days
            earliest_completion = today + timedelta(days=remaining_work_days + current_delay)
            if earliest_completion > order.due_date:
                due_date_at_risk = True
                estimated_delay_days = (earliest_completion - order.due_date).days

        return {
            "remaining_hours": float(remaining_hours),
            "due_date_at_risk": due_date_at_risk,
            "estimated_delay_days": estimated_delay_days,
        }

    async def _generate_recommendation(
        self,
        operation: Operation,
        order: Order,
        severity: str,
        impact: dict,
    ) -> str:
        """Generate recommendation using Claude AI with historical context, or rule-based fallback."""
        # Try AI recommendation
        if self._client:
            try:
                return await self._generate_with_claude(operation, order, severity, impact)
            except Exception:
                logger.exception("deadline_monitor.claude_failed, using fallback")

        return self._generate_rule_based(operation, severity)

    async def _generate_with_claude(
        self,
        operation: Operation,
        order: Order,
        severity: str,
        impact: dict,
    ) -> str:
        """Generate recommendation using Claude with historical similar orders."""
        # Find similar orders
        context_parts = [
            f"Zakázka: {order.number}, priorita: {order.priority.value}",
            f"Operace: {operation.name} (seq. {operation.sequence}), "
            f"trvání: {operation.duration_hours}h",
            f"Závažnost: {severity}",
        ]
        if order.due_date:
            context_parts.append(f"Termín zakázky: {order.due_date.isoformat()}")
        if impact["due_date_at_risk"]:
            context_parts.append(
                f"Odhadované zpoždění: {impact['estimated_delay_days']} dní"
            )

        # Try to get similar orders for context
        try:
            embedding_svc = EmbeddingService(self.db)
            similar = await embedding_svc.find_similar(order.id, limit=3)
            if similar:
                context_parts.append("\nPodobné historické zakázky:")
                for s in similar:
                    context_parts.append(
                        f"- {s.order_number} (stav: {s.status}, "
                        f"podobnost: {s.similarity:.0%})"
                    )
                    if s.note:
                        context_parts.append(f"  Poznámka: {s.note[:200]}")

                    # Load operations of similar order to check historical delays
                    sim_ops_stmt = (
                        select(Operation)
                        .where(Operation.order_id == s.order_id)
                        .order_by(Operation.sequence)
                    )
                    sim_ops_result = await self.db.execute(sim_ops_stmt)
                    sim_ops = sim_ops_result.scalars().all()
                    for sop in sim_ops:
                        if sop.actual_end and sop.planned_end:
                            delay = (sop.actual_end - sop.planned_end).total_seconds() / 3600
                            if abs(delay) > 1:
                                sign = "+" if delay > 0 else ""
                                context_parts.append(
                                    f"  Op. {sop.name}: {sign}{delay:.0f}h vs plán"
                                )
        except Exception:
            logger.warning("deadline_monitor.similar_orders_failed")

        user_message = "\n".join(context_parts)

        response = await self._client.messages.create(  # type: ignore[union-attr]
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            timeout=_TIMEOUT_SECONDS,
        )

        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content += block.text

        return text_content.strip()[:500]

    def _generate_rule_based(self, operation: Operation, severity: str) -> str:
        """Generate rule-based recommendation when Claude is not available."""
        op_name_lower = (operation.name or "").lower()

        if severity == "critical":
            if "svař" in op_name_lower:
                return (
                    "Zvažte druhou směnu nebo subdodávku svařování. "
                    "Kontaktujte vedoucího výroby pro přeorganizování kapacit."
                )
            if "ndt" in op_name_lower or "kontrola" in op_name_lower:
                return (
                    "Kontaktujte externího NDT inspektora pro urychlení kontroly. "
                    "Ověřte dostupnost s certifikovaným pracovištěm."
                )
            if "materiál" in op_name_lower or "příjem" in op_name_lower:
                return (
                    "Urgentně ověřte stav dodávky materiálu u dodavatele. "
                    "Zvažte alternativního dodavatele pro urychlení."
                )
            return (
                "Operace je po termínu. Přehodnoťte kapacity a zvažte "
                "přesčas nebo přeorganizování priorit."
            )

        if severity == "warning":
            return (
                "Ověřte postup s vedoucím výroby. Zvažte přeorganizování "
                "priorit nebo nasazení dodatečných kapacit."
            )

        return "Operace se blíží termínu. Sledujte postup a připravte záložní plán."

    async def _should_notify(self, operation_id, severity: str) -> bool:  # type: ignore[no-untyped-def]
        """Check if notification should be sent (deduplicate within 24h)."""
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        op_result = await self.db.execute(
            select(Operation).where(Operation.id == operation_id)
        )
        op = op_result.scalar_one_or_none()
        if not op:
            return True

        order_result = await self.db.execute(
            select(Order).where(Order.id == op.order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            return True

        # Check if notification with same order+operation already sent in 24h
        title_prefix = f"{order.number}: {op.name}"
        dedup_stmt = (
            select(Notification)
            .where(
                and_(
                    Notification.type == NotificationType.DEADLINE_WARNING,
                    Notification.created_at >= cutoff,
                    Notification.title.startswith(title_prefix),
                )
            )
            .limit(1)
        )
        existing = await self.db.execute(dedup_stmt)
        existing_notification = existing.scalar_one_or_none()

        if existing_notification:
            # Allow escalation: if new severity is worse, still send
            severity_rank = {"info": 0, "warning": 1, "critical": 2}
            existing_severity = "info"
            for sev_key, sev_cz in _SEVERITY_CZECH.items():
                if sev_cz in existing_notification.title:
                    existing_severity = sev_key
                    break

            if severity_rank.get(severity, 0) <= severity_rank.get(existing_severity, 0):
                logger.info(
                    "deadline_monitor.dedup_skip op=%s severity=%s existing=%s",
                    op.name, severity, existing_severity,
                )
                return False

        return True
