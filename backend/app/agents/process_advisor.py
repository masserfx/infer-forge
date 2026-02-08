"""Process advisor agent for analyzing workflow inefficiencies.

Analyzes system data (DLQ entries, reclassified emails, late orders, etc.)
to generate actionable insights for process improvement. Uses Claude API
when available, otherwise falls back to rule-based analysis.
"""

import logging
from datetime import UTC, datetime, timedelta

from anthropic import AsyncAnthropic
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calculation import Calculation, CalculationStatus
from app.models.dead_letter import DeadLetterEntry
from app.models.inbox import InboxMessage, InboxStatus
from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)

_MODEL: str = "claude-sonnet-4-20250514"
_MAX_TOKENS: int = 2048
_TIMEOUT_SECONDS: float = 45.0

_SYSTEM_PROMPT: str = """Jsi procesni advisor pro strojírenskou firmu Infer s.r.o.

Analyzuješ data z orchestračního systému za poslední týden a identifikuješ procesní neefektivity.
Tvým cílem je navrhnout 3-5 konkrétních vylepšení pro automatizační pipeline.

Zaměř se na:
1. Emaily padající do DLQ (Dead Letter Queue) - opakující se chyby
2. Reklasifikované emaily - špatná klasifikace, chybějící vzory
3. Opravené kalkulace - kde AI agent selhal
4. Zakázky po termínu - rizikové signály, které systém nezachytil

Každý návrh musí být:
- KONKRÉTNÍ: ne obecné rady, ale specifické akce (např. "přidat regex vzor pro objednávková čísla formátu ABC-1234")
- MĚŘITELNÝ: jak poznáme, že se problém vyřešil
- PROVEDITELNÝ: něco, co lze implementovat do systému

Vrat seznam 3-5 návrhů, každý s:
- title: krátký výstižný název (max 60 znaků)
- description: detailní popis problému a navrhované řešení (2-4 věty)
- severity: "info" (optimalizace), "warning" (časté problémy), "critical" (blokující chyby)
- category: "classification", "parsing", "calculation", "scheduling", nebo "quality"
"""


class ProcessAdvisorAgent:
    """Agent for generating weekly process improvement insights.

    Analyzes orchestration pipeline data to identify recurring issues and
    suggest concrete improvements to automation rules and patterns.

    Args:
        api_key: Anthropic API key for Claude analysis. If None, uses rule-based analysis.
    """

    def __init__(self, api_key: str | None = None):
        self._client = AsyncAnthropic(api_key=api_key) if api_key else None

    async def generate_weekly_insights(self, db: AsyncSession) -> list[dict]:
        """Generate process improvement insights based on last week's data.

        Args:
            db: SQLAlchemy async session.

        Returns:
            List of insights, each with: title, description, severity, category.
        """
        logger.info("process_advisor.started")

        # Gather metrics from last 7 days
        week_ago = datetime.now(UTC) - timedelta(days=7)
        metrics = await self._gather_metrics(db, week_ago)

        # Use Claude if API key available, otherwise rule-based
        if self._client:
            insights = await self._generate_with_claude(metrics)
        else:
            insights = self._generate_rule_based(metrics)

        logger.info("process_advisor.completed insights=%d", len(insights))
        return insights

    async def _gather_metrics(self, db: AsyncSession, since: datetime) -> dict:
        """Gather metrics from the database for analysis.

        Args:
            db: Database session.
            since: Start date for metrics (typically 7 days ago).

        Returns:
            Dict with counts and examples of various process issues.
        """
        metrics: dict = {
            "period_days": 7,
            "dlq_entries": [],
            "reclassified_emails": [],
            "corrected_calculations": [],
            "late_orders": [],
        }

        # DLQ entries
        dlq_stmt = (
            select(DeadLetterEntry)
            .where(
                and_(
                    DeadLetterEntry.created_at >= since,
                    DeadLetterEntry.resolved == False,  # noqa: E712
                )
            )
            .order_by(DeadLetterEntry.created_at.desc())
            .limit(20)
        )
        dlq_result = await db.execute(dlq_stmt)
        dlq_entries = dlq_result.scalars().all()
        metrics["dlq_entries"] = [
            {
                "stage": entry.stage,
                "error_message": entry.error_message[:200] if entry.error_message else None,
                "retry_count": entry.retry_count,
            }
            for entry in dlq_entries
        ]

        # Emails that were reclassified (status changed from CLASSIFIED to REVIEW)
        reclassified_stmt = (
            select(InboxMessage)
            .where(
                and_(
                    InboxMessage.created_at >= since,
                    InboxMessage.status == InboxStatus.REVIEW,
                    InboxMessage.needs_review == True,  # noqa: E712
                )
            )
            .limit(20)
        )
        reclassified_result = await db.execute(reclassified_stmt)
        reclassified = reclassified_result.scalars().all()
        metrics["reclassified_emails"] = [
            {
                "subject": msg.subject[:100],
                "classification": msg.classification.value if msg.classification else None,
                "confidence": float(msg.confidence) if msg.confidence else 0.0,
            }
            for msg in reclassified
        ]

        # Calculations that were corrected after initial draft
        # (heuristic: multiple calculations for same order, latest is APPROVED)
        calc_stmt = (
            select(Calculation.order_id, func.count(Calculation.id).label("calc_count"))
            .where(Calculation.created_at >= since)
            .group_by(Calculation.order_id)
            .having(func.count(Calculation.id) > 1)
        )
        calc_result = await db.execute(calc_stmt)
        calc_rows = calc_result.fetchall()
        metrics["corrected_calculations"] = [
            {"order_id": str(row.order_id), "count": row.calc_count} for row in calc_rows
        ]

        # Orders past due date
        today = datetime.now(UTC).date()
        late_stmt = (
            select(Order)
            .where(
                and_(
                    Order.due_date < today,
                    Order.status.in_(
                        [
                            OrderStatus.POPTAVKA,
                            OrderStatus.NABIDKA,
                            OrderStatus.OBJEDNAVKA,
                            OrderStatus.VYROBA,
                        ]
                    ),
                )
            )
            .limit(20)
        )
        late_result = await db.execute(late_stmt)
        late_orders = late_result.scalars().all()
        metrics["late_orders"] = [
            {
                "number": order.number,
                "status": order.status.value,
                "due_date": order.due_date.isoformat() if order.due_date else None,
                "days_late": (today - order.due_date).days if order.due_date else 0,
            }
            for order in late_orders
        ]

        logger.info(
            "process_advisor.metrics_gathered dlq=%d reclassified=%d corrected_calc=%d late=%d",
            len(metrics["dlq_entries"]),
            len(metrics["reclassified_emails"]),
            len(metrics["corrected_calculations"]),
            len(metrics["late_orders"]),
        )

        return metrics

    async def _generate_with_claude(self, metrics: dict) -> list[dict]:
        """Generate insights using Claude API.

        Args:
            metrics: Gathered metrics dict.

        Returns:
            List of insight dicts.
        """
        if not self._client:
            logger.warning("process_advisor.no_client")
            return self._generate_rule_based(metrics)

        # Build prompt from metrics
        user_message = self._build_metrics_summary(metrics)

        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                        + "\n\nVygeneruj 3-5 konkrétních doporučení ve formátu JSON array:\n"
                        '[{"title": "...", "description": "...", "severity": "info|warning|critical", '
                        '"category": "classification|parsing|calculation|scheduling|quality"}]',
                    }
                ],
                timeout=_TIMEOUT_SECONDS,
            )

            # Extract text content
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            # Parse JSON from response
            import json

            # Try to find JSON array in response
            start_idx = text_content.find("[")
            end_idx = text_content.rfind("]")
            if start_idx >= 0 and end_idx > start_idx:
                json_str = text_content[start_idx : end_idx + 1]
                insights = json.loads(json_str)
                logger.info("process_advisor.claude_success insights=%d", len(insights))
                return insights
            else:
                logger.warning("process_advisor.no_json_in_response")
                return self._generate_rule_based(metrics)

        except TimeoutError:
            logger.warning("process_advisor.timeout")
            return self._generate_rule_based(metrics)
        except Exception:
            logger.exception("process_advisor.api_error")
            return self._generate_rule_based(metrics)

    def _build_metrics_summary(self, metrics: dict) -> str:
        """Build human-readable summary of metrics for Claude.

        Args:
            metrics: Gathered metrics dict.

        Returns:
            Formatted text summary.
        """
        parts = [f"ANALÝZA ZA POSLEDNÍCH {metrics['period_days']} DNÍ\n"]

        # DLQ entries
        dlq_count = len(metrics["dlq_entries"])
        if dlq_count > 0:
            parts.append(f"\n1. DEAD LETTER QUEUE: {dlq_count} neúspěšných zpracování")
            stage_counts: dict[str, int] = {}
            for entry in metrics["dlq_entries"]:
                stage_counts[entry["stage"]] = stage_counts.get(entry["stage"], 0) + 1
            for stage, count in sorted(stage_counts.items(), key=lambda x: -x[1]):
                parts.append(f"   - {stage}: {count}x")
            # Sample error messages
            parts.append("   Příklady chyb:")
            for entry in metrics["dlq_entries"][:3]:
                if entry["error_message"]:
                    parts.append(f"   - {entry['error_message'][:150]}")

        # Reclassified emails
        reclassified_count = len(metrics["reclassified_emails"])
        if reclassified_count > 0:
            parts.append(f"\n2. REKLASIFIKOVANÉ EMAILY: {reclassified_count} vyžadovalo manuální kontrolu")
            # Show low-confidence classifications
            low_conf = [e for e in metrics["reclassified_emails"] if e["confidence"] < 0.7]
            if low_conf:
                parts.append(f"   - {len(low_conf)}x nízká confidence (<0.7)")
            parts.append("   Příklady předmětů:")
            for email in metrics["reclassified_emails"][:3]:
                parts.append(
                    f"   - {email['subject']} (klasifikace: {email['classification']}, "
                    f"confidence: {email['confidence']:.2f})"
                )

        # Corrected calculations
        corrected_count = len(metrics["corrected_calculations"])
        if corrected_count > 0:
            parts.append(f"\n3. OPRAVENÉ KALKULACE: {corrected_count} zakázek má vícenásobné kalkulace")
            parts.append("   → Indikuje, že AI agent vytvořil nesprávnou kalkulaci")

        # Late orders
        late_count = len(metrics["late_orders"])
        if late_count > 0:
            parts.append(f"\n4. ZAKÁZKY PO TERMÍNU: {late_count} zakázek překročilo termín")
            avg_days = (
                sum(o["days_late"] for o in metrics["late_orders"]) / late_count
                if late_count
                else 0
            )
            parts.append(f"   - Průměrné zpoždění: {avg_days:.1f} dní")
            parts.append("   Příklady:")
            for order in metrics["late_orders"][:3]:
                parts.append(
                    f"   - {order['number']}: {order['status']}, "
                    f"{order['days_late']} dní po termínu"
                )

        return "\n".join(parts)

    def _generate_rule_based(self, metrics: dict) -> list[dict]:
        """Generate insights using rule-based heuristics.

        Args:
            metrics: Gathered metrics dict.

        Returns:
            List of insight dicts.
        """
        insights: list[dict] = []

        # DLQ analysis
        dlq_count = len(metrics["dlq_entries"])
        if dlq_count >= 5:
            stage_counts: dict[str, int] = {}
            for entry in metrics["dlq_entries"]:
                stage_counts[entry["stage"]] = stage_counts.get(entry["stage"], 0) + 1

            most_common_stage = max(stage_counts.items(), key=lambda x: x[1])
            insights.append(
                {
                    "title": f"Časté chyby ve fázi {most_common_stage[0]}",
                    "description": f"{most_common_stage[1]} emailů selhalo ve fázi "
                    f"{most_common_stage[0]} tento týden. Zkontrolujte validační pravidla "
                    f"a error handling pro tuto fázi. Pravděpodobně chybí zpracování "
                    f"okrajových případů nebo specifických formátů emailů.",
                    "severity": "warning" if most_common_stage[1] >= 10 else "info",
                    "category": "quality",
                }
            )

        # Reclassified emails analysis
        reclassified_count = len(metrics["reclassified_emails"])
        if reclassified_count >= 3:
            low_conf_count = sum(
                1 for e in metrics["reclassified_emails"] if e["confidence"] < 0.7
            )
            insights.append(
                {
                    "title": "Nízká přesnost klasifikace emailů",
                    "description": f"{reclassified_count} emailů vyžadovalo manuální reklasifikaci, "
                    f"{low_conf_count} z nich mělo confidence <0.7. Zvažte přidání nových "
                    f"klíčových slov do heuristického klasifikátoru nebo přetrénování AI modelu "
                    f"na reálných datech z produkce.",
                    "severity": "warning",
                    "category": "classification",
                }
            )

        # Corrected calculations
        corrected_count = len(metrics["corrected_calculations"])
        if corrected_count >= 2:
            insights.append(
                {
                    "title": "AI kalkulační agent vytváří nesprávné kalkulace",
                    "description": f"{corrected_count} zakázek má vícenásobné kalkulace, "
                    f"což indikuje, že první kalkulace byla chybná. Zkontrolujte prompt "
                    f"kalkulačního agenta a přidejte validační pravidla pro odhalení "
                    f"nerealistických cen nebo chybějících položek.",
                    "severity": "warning",
                    "category": "calculation",
                }
            )

        # Late orders
        late_count = len(metrics["late_orders"])
        if late_count >= 5:
            avg_days = (
                sum(o["days_late"] for o in metrics["late_orders"]) / late_count
                if late_count
                else 0
            )
            insights.append(
                {
                    "title": f"Zakázky často překračují termíny (průměr {avg_days:.1f} dní)",
                    "description": f"{late_count} zakázek je po termínu s průměrným zpožděním "
                    f"{avg_days:.1f} dní. Implementujte automatické upozornění 3 dny před "
                    f"termínem a zvažte prediktivní model pro odhad rizika zpoždění na základě "
                    f"priority, komplexity a kapacity.",
                    "severity": "warning" if avg_days > 5 else "info",
                    "category": "scheduling",
                }
            )

        # Default message if no issues
        if not insights:
            insights.append(
                {
                    "title": "Systém funguje bez větších problémů",
                    "description": "Tento týden nebyly identifikovány žádné závažné procesní "
                    "neefektivity. Orchestrační pipeline zpracovává emaily bez opakujících se "
                    "chyb. Doporučuji pravidelně monitorovat metriky kvality.",
                    "severity": "info",
                    "category": "quality",
                }
            )

        logger.info("process_advisor.rule_based_generated insights=%d", len(insights))
        return insights
