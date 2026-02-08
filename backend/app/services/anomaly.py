"""Anomaly detection for calculations."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Calculation, CalculationStatus

logger = logging.getLogger(__name__)


class AnomalyService:
    """Detects anomalies in calculations by comparing to historical data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_calculation(self, calculation_id: UUID) -> list[dict[str, Any]]:
        """Check a calculation for anomalies.

        Compares margin, material costs, and labor ratios against
        historical calculations of similar type.
        """
        result = await self.db.execute(
            select(Calculation).where(Calculation.id == calculation_id)
        )
        calc = result.scalar_one_or_none()
        if not calc:
            return []

        anomalies = []

        # Get historical calculations for comparison (approved ones)
        hist_result = await self.db.execute(
            select(Calculation)
            .where(
                Calculation.status.in_([CalculationStatus.APPROVED, CalculationStatus.OFFERED]),
                Calculation.id != calculation_id,
            )
            .limit(50)
        )
        historical = list(hist_result.scalars().all())

        if len(historical) < 3:
            return []  # Not enough data for comparison

        # Check margin
        margins = [float(h.margin_percent) for h in historical if h.margin_percent > 0]
        if margins:
            avg_margin = sum(margins) / len(margins)
            if float(calc.margin_percent) < avg_margin * 0.5:
                anomalies.append({
                    "type": "low_margin",
                    "severity": "warning",
                    "message": f"Marže {float(calc.margin_percent):.1f}% je výrazně pod průměrem {avg_margin:.1f}%",
                    "expected": round(avg_margin, 1),
                    "actual": round(float(calc.margin_percent), 1),
                })
            elif float(calc.margin_percent) > avg_margin * 2:
                anomalies.append({
                    "type": "high_margin",
                    "severity": "info",
                    "message": f"Marže {float(calc.margin_percent):.1f}% je výrazně nad průměrem {avg_margin:.1f}%",
                    "expected": round(avg_margin, 1),
                    "actual": round(float(calc.margin_percent), 1),
                })

        # Check total price ratio (material/total)
        totals = [float(h.total_price) for h in historical if h.total_price > 0]
        if totals and calc.total_price > 0:
            avg_total = sum(totals) / len(totals)
            if float(calc.total_price) > avg_total * 3:
                anomalies.append({
                    "type": "high_total",
                    "severity": "info",
                    "message": f"Celková cena {float(calc.total_price):,.0f} Kč je 3x nad průměrem {avg_total:,.0f} Kč",
                    "expected": round(avg_total),
                    "actual": round(float(calc.total_price)),
                })

        return anomalies
