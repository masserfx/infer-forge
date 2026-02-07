"""Calculation agent for automatic cost estimation.

Uses Anthropic Claude API with structured tool_use output to estimate
material costs, labor hours, and margins for steel fabrication orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from anthropic import AsyncAnthropic

logger = structlog.get_logger(__name__)

# Default hourly rate for labor in CZK (configurable)
_DEFAULT_HOURLY_RATE_CZK: float = 850.0

# Anthropic model used for cost estimation
_MODEL: str = "claude-sonnet-4-20250514"

# Maximum tokens for the estimation response
_MAX_TOKENS: int = 4096

# Timeout in seconds for the API call
_TIMEOUT_SECONDS: float = 60.0

# Tool definition for structured cost estimation output
_ESTIMATE_TOOL: dict[str, object] = {
    "name": "estimate_costs",
    "description": (
        "Estimate manufacturing costs for steel fabrication items. "
        "Include material costs, labor hours, overhead, and recommended margin. "
        "Provide per-item breakdown with reasoning."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "material_cost_czk": {
                "type": "number",
                "description": "Total material cost in CZK for all items.",
            },
            "labor_hours": {
                "type": "number",
                "description": "Total estimated labor hours for all items.",
            },
            "overhead_czk": {
                "type": "number",
                "description": (
                    "Estimated overhead costs in CZK (energy, consumables, machine time, etc.)."
                ),
            },
            "margin_percent": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": (
                    "Recommended profit margin in percent (0-100). "
                    "Consider complexity, risk, competition, and market conditions."
                ),
            },
            "items": {
                "type": "array",
                "description": "Per-item cost breakdown.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Item name or description.",
                        },
                        "material_cost_czk": {
                            "type": "number",
                            "description": "Material cost for this item in CZK.",
                        },
                        "labor_hours": {
                            "type": "number",
                            "description": "Labor hours for this item.",
                        },
                        "notes": {
                            "type": "string",
                            "description": (
                                "Brief notes about estimation assumptions, "
                                "complexity factors, or special considerations."
                            ),
                        },
                    },
                    "required": ["name", "material_cost_czk", "labor_hours", "notes"],
                },
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "Overall reasoning for the estimate in Czech. "
                    "Explain key assumptions, market rates used, complexity factors, "
                    "and why the margin was set at the given level."
                ),
            },
        },
        "required": [
            "material_cost_czk",
            "labor_hours",
            "overhead_czk",
            "margin_percent",
            "items",
            "reasoning",
        ],
    },
}

# System prompt describing the estimation task and company context
_SYSTEM_PROMPT: str = """Jsi AI asistent pro kalkulace ve strojírenské firmě Infer s.r.o.

**Kontext firmy:**
- Výroba potrubních dílů (kolena, T-kusy, redukce, příruby) z uhlové a nerezové oceli
- Svařované konstrukce a svařence dle výkresové dokumentace
- Ocelové konstrukce (nosné, podpůrné, technologické)
- Montáže průmyslových zařízení a potrubí
- Certifikace ISO 9001:2016, specializace na NDT (nedestruktivní testování)

**Typické ceny materiálů (2025, orientační):**
- Ocel konstrukční S235 (černá): 30-35 Kč/kg
- Ocel S355J2+N: 35-42 Kč/kg
- Nerezová ocel 304 (1.4301): 110-140 Kč/kg
- Nerezová ocel 316L (1.4404): 150-180 Kč/kg
- Příruby dle DN: DN50 ~200 Kč/ks, DN100 ~450 Kč/ks, DN200 ~1200 Kč/ks
- Svařovací materiály: 150-300 Kč/kg (dle typu)

**Sazby práce:**
- Hodinová sazba: 850 Kč/hod (lze konfigurovat)
- Svařování: 0.5-2 hod/metr švu (dle tloušťky, pozice, materiálu)
- Obrábění: 0.3-1.5 hod/kus (dle složitosti)
- Montáž: 1-4 hod/spojení (dle přístupnosti)
- Příprava materiálu (řezání, rovnání): 0.2-0.5 hod/kus

**Režijní náklady:**
- Typicky 15-25% z přímých nákladů (materiál + práce)
- Zahrnuje: energie, spotřební materiál (kotouče, elektrody), opotřebení nástrojů,
  administrativu, certifikaci, pojištění

**Marže:**
- Standardní zakázky: 20-30%
- Komplexní/rizikové projekty: 30-40%
- Velkosériová výroba: 15-25%
- Konkurenční nabídky: 10-20%

**Tvůj úkol:**
1. Odhadni materiálové náklady na základě specifikace (materiál, rozměry, množství)
2. Spočítej pracnost v hodinách (svařování, obrábění, montáž, příprava)
3. Přidej režijní náklady (energie, spotřební materiál, atd.)
4. Navrhni vhodnou marži dle složitosti a rizika zakázky
5. Pro každou položku poskytni rozpad nákladů a poznámky

Buď konzervativní v odhadech - lepší nadhodnotit pracnost než podhodno. Při nejistotě
ohledně složitosti přidej rezervu. Vždy vysvětli své uvažování.

Použij nástroj estimate_costs pro vrácení strukturovaného výsledku."""


@dataclass(frozen=True, slots=True)
class ItemEstimate:
    """Cost estimate for a single item.

    Attributes:
        name: Item name or description.
        material_cost_czk: Material cost in CZK.
        labor_hours: Estimated labor hours.
        notes: Assumptions and notes about the estimate.
    """

    name: str
    material_cost_czk: float
    labor_hours: float
    notes: str


@dataclass(frozen=True, slots=True)
class CalculationEstimate:
    """Complete cost estimation result.

    Attributes:
        material_cost_czk: Total material cost in CZK.
        labor_hours: Total labor hours.
        labor_cost_czk: Total labor cost in CZK (labor_hours * hourly_rate).
        overhead_czk: Estimated overhead costs in CZK.
        margin_percent: Recommended profit margin percentage.
        total_czk: Total estimated price including margin.
        breakdown: Per-item cost breakdown.
        reasoning: Overall reasoning and assumptions in Czech.
    """

    material_cost_czk: float
    labor_hours: float
    labor_cost_czk: float
    overhead_czk: float
    margin_percent: float
    total_czk: float
    breakdown: list[ItemEstimate] = field(default_factory=list)
    reasoning: str = ""

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        if self.margin_percent < 0.0 or self.margin_percent > 100.0:
            object.__setattr__(
                self,
                "margin_percent",
                max(0.0, min(100.0, self.margin_percent)),
            )


class CalculationAgent:
    """AI agent for estimating manufacturing costs.

    Uses Anthropic Claude API with structured tool_use output to estimate
    material costs, labor hours, overhead, and profit margins for steel
    fabrication orders.

    Args:
        api_key: Anthropic API key for authentication.
        hourly_rate_czk: Labor hourly rate in CZK (default: 850.0).

    Example:
        >>> agent = CalculationAgent(api_key="sk-ant-...")
        >>> result = await agent.estimate(
        ...     description="Výroba ocelové konstrukce",
        ...     items=[
        ...         {
        ...             "name": "Nosník HEB200",
        ...             "material": "S235JR",
        ...             "dimension": "200x200x9mm, délka 6m",
        ...             "quantity": 10,
        ...             "unit": "ks",
        ...         },
        ...     ],
        ... )
        >>> result.total_czk
        125000.0
    """

    def __init__(
        self,
        api_key: str,
        hourly_rate_czk: float = _DEFAULT_HOURLY_RATE_CZK,
    ) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._hourly_rate = hourly_rate_czk

    async def estimate(
        self,
        description: str,
        items: list[dict[str, object]],
    ) -> CalculationEstimate:
        """Estimate costs for a set of fabrication items.

        Args:
            description: Order description providing context (e.g., "Výroba kolena DN200").
            items: List of items to estimate. Each dict should contain:
                - name: Item name (e.g., "Koleno 90° DN200 PN16")
                - material: Material specification (e.g., "S235JR", "1.4404")
                - dimension: Dimensions (e.g., "DN200, tl. 6mm")
                - quantity: Quantity (numeric)
                - unit: Unit (e.g., "ks", "m", "kg")

        Returns:
            CalculationEstimate with costs, hours, margin, and per-item breakdown.
        """
        log = logger.bind(description=description[:100], item_count=len(items))
        log.info("calculation_estimate.started")

        user_message = self._build_user_message(description, items)

        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                tools=[_ESTIMATE_TOOL],  # type: ignore[list-item]
                tool_choice={"type": "tool", "name": "estimate_costs"},
                messages=[{"role": "user", "content": user_message}],
                timeout=_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            log.warning("calculation_estimate.timeout")
            return CalculationEstimate(
                material_cost_czk=0.0,
                labor_hours=0.0,
                labor_cost_czk=0.0,
                overhead_czk=0.0,
                margin_percent=0.0,
                total_czk=0.0,
                reasoning="Kalkulace selhala: vypršení časového limitu API volání.",
            )
        except Exception:
            log.exception("calculation_estimate.api_error")
            return CalculationEstimate(
                material_cost_czk=0.0,
                labor_hours=0.0,
                labor_cost_czk=0.0,
                overhead_czk=0.0,
                margin_percent=0.0,
                total_czk=0.0,
                reasoning="Kalkulace selhala: neočekávaná chyba při volání API.",
            )

        return self._parse_response(response, log)

    @staticmethod
    def _build_user_message(description: str, items: list[dict[str, object]]) -> str:
        """Build the user message from order description and items.

        Args:
            description: Order description.
            items: List of items with name, material, dimension, quantity, unit.

        Returns:
            Formatted user message string.
        """
        items_text = ""
        for idx, item in enumerate(items, start=1):
            name = item.get("name", "Bez názvu")
            material = item.get("material", "Nespecifikováno")
            dimension = item.get("dimension", "")
            quantity = item.get("quantity", 1)
            unit = item.get("unit", "ks")

            items_text += (
                f"\n{idx}. **{name}**\n"
                f"   - Materiál: {material}\n"
                f"   - Rozměry: {dimension}\n"
                f"   - Množství: {quantity} {unit}\n"
            )

        return (
            f"Proveď kalkulaci nákladů pro následující zakázku:\n\n"
            f"**POPIS ZAKÁZKY:**\n{description}\n\n"
            f"**POLOŽKY:**{items_text}\n\n"
            f"Odhadni materiálové náklady, pracnost v hodinách, režii a navrhni "
            f"vhodnou marži. Pro každou položku poskytni rozpad a poznámky."
        )

    def _parse_response(
        self,
        response: object,
        log: structlog.stdlib.BoundLogger,
    ) -> CalculationEstimate:
        """Parse the Anthropic API response into a CalculationEstimate.

        Args:
            response: The raw API response from Anthropic.
            log: Bound structlog logger for contextual logging.

        Returns:
            Parsed CalculationEstimate.
        """
        # Extract tool_use block from response content
        tool_input: dict[str, object] | None = None
        for block in response.content:  # type: ignore[attr-defined]
            if block.type == "tool_use" and block.name == "estimate_costs":
                tool_input = block.input  # type: ignore[assignment]
                break

        if tool_input is None:
            log.error(
                "calculation_estimate.no_tool_use_block",
                response_content=str(response.content),  # type: ignore[attr-defined]
            )
            return CalculationEstimate(
                material_cost_czk=0.0,
                labor_hours=0.0,
                labor_cost_czk=0.0,
                overhead_czk=0.0,
                margin_percent=0.0,
                total_czk=0.0,
                reasoning="Kalkulace selhala: API nevrátilo očekávaný tool_use blok.",
            )

        # Extract and validate fields
        material_cost = self._parse_float(tool_input.get("material_cost_czk", 0.0))
        labor_hours = self._parse_float(tool_input.get("labor_hours", 0.0))
        overhead = self._parse_float(tool_input.get("overhead_czk", 0.0))
        margin_percent = self._parse_float(tool_input.get("margin_percent", 0.0))
        margin_percent = max(0.0, min(100.0, margin_percent))
        reasoning = str(tool_input.get("reasoning", ""))

        # Calculate derived values
        labor_cost = labor_hours * self._hourly_rate
        direct_costs = material_cost + labor_cost + overhead
        margin_amount = direct_costs * (margin_percent / 100.0)
        total = direct_costs + margin_amount

        # Parse item breakdown
        breakdown: list[ItemEstimate] = []
        items_raw = tool_input.get("items", [])
        if isinstance(items_raw, list):
            for item_data in items_raw:
                if isinstance(item_data, dict):
                    breakdown.append(
                        ItemEstimate(
                            name=str(item_data.get("name", "Bez názvu")),
                            material_cost_czk=self._parse_float(
                                item_data.get("material_cost_czk", 0.0)
                            ),
                            labor_hours=self._parse_float(item_data.get("labor_hours", 0.0)),
                            notes=str(item_data.get("notes", "")),
                        )
                    )

        result = CalculationEstimate(
            material_cost_czk=material_cost,
            labor_hours=labor_hours,
            labor_cost_czk=labor_cost,
            overhead_czk=overhead,
            margin_percent=margin_percent,
            total_czk=total,
            breakdown=breakdown,
            reasoning=reasoning,
        )

        log.info(
            "calculation_estimate.completed",
            material_cost=result.material_cost_czk,
            labor_hours=result.labor_hours,
            labor_cost=result.labor_cost_czk,
            overhead=result.overhead_czk,
            margin_percent=result.margin_percent,
            total=result.total_czk,
            items_count=len(breakdown),
        )

        return result

    @staticmethod
    def _parse_float(value: object) -> float:
        """Parse a value to float, returning 0.0 if invalid.

        Args:
            value: Value to parse.

        Returns:
            Parsed float or 0.0 if parsing fails.
        """
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0
