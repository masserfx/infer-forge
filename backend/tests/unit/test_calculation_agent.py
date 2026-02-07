"""Unit tests for calculation agent (mocked API)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.calculation_agent import (
    CalculationAgent,
    CalculationEstimate,
    ItemEstimate,
)


def _make_tool_use_block(
    material_cost_czk: float = 5000.0,
    labor_hours: float = 10.0,
    overhead_czk: float = 1000.0,
    margin_percent: float = 25.0,
    items: list[dict[str, object]] | None = None,
    reasoning: str = "Test reasoning",
) -> MagicMock:
    """Create a mock tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = "estimate_costs"

    if items is None:
        items = [
            {
                "name": "Test Item",
                "material_cost_czk": 5000.0,
                "labor_hours": 10.0,
                "notes": "Test notes",
            }
        ]

    block.input = {
        "material_cost_czk": material_cost_czk,
        "labor_hours": labor_hours,
        "overhead_czk": overhead_czk,
        "margin_percent": margin_percent,
        "items": items,
        "reasoning": reasoning,
    }
    return block


def _make_response(blocks: list) -> MagicMock:
    """Create a mock API response."""
    response = MagicMock()
    response.content = blocks
    return response


class TestItemEstimate:
    """Tests for ItemEstimate dataclass."""

    def test_valid_item_estimate(self) -> None:
        """Test creating a valid item estimate."""
        item = ItemEstimate(
            name="Koleno DN200 PN16",
            material_cost_czk=1200.0,
            labor_hours=2.5,
            notes="Materiál nerez 1.4404, svařování TIG",
        )
        assert item.name == "Koleno DN200 PN16"
        assert item.material_cost_czk == 1200.0
        assert item.labor_hours == 2.5
        assert item.notes == "Materiál nerez 1.4404, svařování TIG"

    def test_item_estimate_frozen(self) -> None:
        """Test that ItemEstimate is frozen (immutable)."""
        item = ItemEstimate(
            name="Test",
            material_cost_czk=100.0,
            labor_hours=1.0,
            notes="Test",
        )
        with pytest.raises(AttributeError):
            item.name = "Modified"  # type: ignore[misc]


class TestCalculationEstimate:
    """Tests for CalculationEstimate dataclass."""

    def test_valid_calculation_estimate(self) -> None:
        """Test creating a valid calculation estimate."""
        items = [
            ItemEstimate(
                name="Item 1",
                material_cost_czk=1000.0,
                labor_hours=5.0,
                notes="Notes",
            )
        ]
        estimate = CalculationEstimate(
            material_cost_czk=1000.0,
            labor_hours=5.0,
            labor_cost_czk=4250.0,
            overhead_czk=500.0,
            margin_percent=20.0,
            total_czk=6900.0,
            breakdown=items,
            reasoning="Test reasoning",
        )
        assert estimate.material_cost_czk == 1000.0
        assert estimate.labor_hours == 5.0
        assert estimate.labor_cost_czk == 4250.0
        assert estimate.overhead_czk == 500.0
        assert estimate.margin_percent == 20.0
        assert estimate.total_czk == 6900.0
        assert len(estimate.breakdown) == 1
        assert estimate.reasoning == "Test reasoning"

    def test_margin_clamping_over_100(self) -> None:
        """Test that margin over 100% is clamped."""
        estimate = CalculationEstimate(
            material_cost_czk=1000.0,
            labor_hours=5.0,
            labor_cost_czk=4250.0,
            overhead_czk=500.0,
            margin_percent=150.0,
            total_czk=10000.0,
        )
        assert estimate.margin_percent == 100.0

    def test_margin_clamping_under_0(self) -> None:
        """Test that negative margin is clamped to 0."""
        estimate = CalculationEstimate(
            material_cost_czk=1000.0,
            labor_hours=5.0,
            labor_cost_czk=4250.0,
            overhead_czk=500.0,
            margin_percent=-10.0,
            total_czk=5000.0,
        )
        assert estimate.margin_percent == 0.0

    def test_default_empty_breakdown(self) -> None:
        """Test that breakdown defaults to empty list."""
        estimate = CalculationEstimate(
            material_cost_czk=0.0,
            labor_hours=0.0,
            labor_cost_czk=0.0,
            overhead_czk=0.0,
            margin_percent=0.0,
            total_czk=0.0,
        )
        assert estimate.breakdown == []
        assert estimate.reasoning == ""


class TestCalculationAgent:
    """Tests for CalculationAgent with mocked API."""

    @pytest.fixture
    def agent(self) -> CalculationAgent:
        """Create agent with test API key."""
        return CalculationAgent(api_key="test-key")

    async def test_estimate_basic_order(self, agent: CalculationAgent) -> None:
        """Test estimating a basic order."""
        mock_response = _make_response(
            [
                _make_tool_use_block(
                    material_cost_czk=5000.0,
                    labor_hours=10.0,
                    overhead_czk=1000.0,
                    margin_percent=25.0,
                    items=[
                        {
                            "name": "Koleno DN200 PN16",
                            "material_cost_czk": 5000.0,
                            "labor_hours": 10.0,
                            "notes": "Nerezová ocel 1.4404, svařování TIG",
                        }
                    ],
                    reasoning="Kalkulace založená na běžných tržních cenách materiálu a práce.",
                ),
            ]
        )

        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.estimate(
                description="Výroba kolena DN200 PN16",
                items=[
                    {
                        "name": "Koleno DN200 PN16",
                        "material": "1.4404",
                        "dimension": "DN200, tl. 6mm",
                        "quantity": 10,
                        "unit": "ks",
                    }
                ],
            )

        assert result.material_cost_czk == 5000.0
        assert result.labor_hours == 10.0
        assert result.labor_cost_czk == 8500.0  # 10 * 850
        assert result.overhead_czk == 1000.0
        assert result.margin_percent == 25.0

        # Calculate expected total: (5000 + 8500 + 1000) * 1.25 = 18125
        assert result.total_czk == 18125.0
        assert len(result.breakdown) == 1
        assert result.breakdown[0].name == "Koleno DN200 PN16"

    async def test_estimate_multiple_items(self, agent: CalculationAgent) -> None:
        """Test estimating multiple items."""
        mock_response = _make_response(
            [
                _make_tool_use_block(
                    material_cost_czk=15000.0,
                    labor_hours=25.0,
                    overhead_czk=3000.0,
                    margin_percent=30.0,
                    items=[
                        {
                            "name": "Nosník HEB200",
                            "material_cost_czk": 10000.0,
                            "labor_hours": 15.0,
                            "notes": "Ocel S235JR, řezání a svařování",
                        },
                        {
                            "name": "Příruba DN100",
                            "material_cost_czk": 5000.0,
                            "labor_hours": 10.0,
                            "notes": "Obrábění a příprava",
                        },
                    ],
                    reasoning="Komplexní zakázka s vyšší pracností.",
                ),
            ]
        )

        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.estimate(
                description="Ocelová konstrukce s přírubami",
                items=[
                    {
                        "name": "Nosník HEB200",
                        "material": "S235JR",
                        "dimension": "200x200x9mm, délka 6m",
                        "quantity": 10,
                        "unit": "ks",
                    },
                    {
                        "name": "Příruba DN100",
                        "material": "S235JR",
                        "dimension": "DN100 PN16",
                        "quantity": 20,
                        "unit": "ks",
                    },
                ],
            )

        assert result.material_cost_czk == 15000.0
        assert result.labor_hours == 25.0
        assert result.margin_percent == 30.0
        assert len(result.breakdown) == 2

    async def test_estimate_custom_hourly_rate(self) -> None:
        """Test agent with custom hourly rate."""
        agent = CalculationAgent(api_key="test-key", hourly_rate_czk=1000.0)

        mock_response = _make_response(
            [
                _make_tool_use_block(
                    material_cost_czk=1000.0,
                    labor_hours=5.0,
                    overhead_czk=200.0,
                    margin_percent=20.0,
                ),
            ]
        )

        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.estimate(
                description="Test",
                items=[{"name": "Test", "material": "S235", "dimension": "100x100", "quantity": 1, "unit": "ks"}],
            )

        # labor_cost should use custom rate: 5 * 1000 = 5000
        assert result.labor_cost_czk == 5000.0

    async def test_estimate_timeout(self, agent: CalculationAgent) -> None:
        """Test handling of API timeout."""
        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=TimeoutError("Request timed out"),
        ):
            result = await agent.estimate(
                description="Test",
                items=[{"name": "Test", "material": "S235", "dimension": "100x100", "quantity": 1, "unit": "ks"}],
            )

        assert result.material_cost_czk == 0.0
        assert result.labor_hours == 0.0
        assert result.total_czk == 0.0
        assert "vypršení" in result.reasoning.lower() or "timeout" in result.reasoning.lower()

    async def test_estimate_api_error(self, agent: CalculationAgent) -> None:
        """Test handling of generic API error."""
        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API error"),
        ):
            result = await agent.estimate(
                description="Test",
                items=[{"name": "Test", "material": "S235", "dimension": "100x100", "quantity": 1, "unit": "ks"}],
            )

        assert result.material_cost_czk == 0.0
        assert result.total_czk == 0.0
        assert "neočekávaná chyba" in result.reasoning.lower()

    async def test_estimate_no_tool_use_block(self, agent: CalculationAgent) -> None:
        """Test handling of response without tool_use block."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Some text response"
        mock_response = _make_response([text_block])

        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.estimate(
                description="Test",
                items=[{"name": "Test", "material": "S235", "dimension": "100x100", "quantity": 1, "unit": "ks"}],
            )

        assert result.total_czk == 0.0
        assert "nevrátilo očekávaný tool_use blok" in result.reasoning

    async def test_estimate_invalid_data_types(self, agent: CalculationAgent) -> None:
        """Test handling of invalid data types in API response."""
        block = _make_tool_use_block()
        # Override with invalid types
        block.input = {
            "material_cost_czk": "invalid",
            "labor_hours": None,
            "overhead_czk": [],
            "margin_percent": {},
            "items": "not a list",
            "reasoning": 123,
        }
        mock_response = _make_response([block])

        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.estimate(
                description="Test",
                items=[{"name": "Test", "material": "S235", "dimension": "100x100", "quantity": 1, "unit": "ks"}],
            )

        # Should handle invalid types gracefully
        assert result.material_cost_czk == 0.0
        assert result.labor_hours == 0.0
        assert result.overhead_czk == 0.0
        assert result.margin_percent == 0.0
        assert result.breakdown == []

    async def test_estimate_missing_item_fields(self, agent: CalculationAgent) -> None:
        """Test handling of items with missing fields."""
        mock_response = _make_response(
            [
                _make_tool_use_block(
                    items=[
                        {
                            "name": "Complete Item",
                            "material_cost_czk": 1000.0,
                            "labor_hours": 5.0,
                            "notes": "Complete",
                        },
                        {
                            # Missing fields
                            "material_cost_czk": 500.0,
                        },
                        "invalid_item",  # Not a dict
                    ]
                ),
            ]
        )

        with patch.object(
            agent._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.estimate(
                description="Test",
                items=[{"name": "Test", "material": "S235", "dimension": "100x100", "quantity": 1, "unit": "ks"}],
            )

        # Should handle partial items gracefully
        assert len(result.breakdown) == 2  # Only valid dicts
        assert result.breakdown[0].name == "Complete Item"
        assert result.breakdown[1].name == "Bez názvu"

    def test_build_user_message(self) -> None:
        """Test user message construction."""
        msg = CalculationAgent._build_user_message(
            description="Výroba kolena",
            items=[
                {
                    "name": "Koleno DN200",
                    "material": "1.4404",
                    "dimension": "DN200, tl. 6mm",
                    "quantity": 10,
                    "unit": "ks",
                }
            ],
        )
        assert "Výroba kolena" in msg
        assert "Koleno DN200" in msg
        assert "1.4404" in msg
        assert "DN200, tl. 6mm" in msg
        assert "10 ks" in msg

    def test_build_user_message_empty_items(self) -> None:
        """Test user message with empty items list."""
        msg = CalculationAgent._build_user_message(
            description="Prázdná zakázka",
            items=[],
        )
        assert "Prázdná zakázka" in msg
        assert "POLOŽKY:" in msg

    def test_build_user_message_missing_fields(self) -> None:
        """Test user message with items missing optional fields."""
        msg = CalculationAgent._build_user_message(
            description="Test",
            items=[
                {
                    "name": "Item with defaults",
                    # Missing material, dimension, quantity, unit
                }
            ],
        )
        assert "Item with defaults" in msg
        assert "Nespecifikováno" in msg  # Default material
        assert "1 ks" in msg  # Default quantity and unit

    def test_parse_float_valid(self) -> None:
        """Test _parse_float with valid values."""
        assert CalculationAgent._parse_float(123.45) == 123.45
        assert CalculationAgent._parse_float(100) == 100.0
        assert CalculationAgent._parse_float("456.78") == 456.78

    def test_parse_float_invalid(self) -> None:
        """Test _parse_float with invalid values returns 0.0."""
        assert CalculationAgent._parse_float("invalid") == 0.0
        assert CalculationAgent._parse_float(None) == 0.0
        assert CalculationAgent._parse_float([]) == 0.0
        assert CalculationAgent._parse_float({}) == 0.0
