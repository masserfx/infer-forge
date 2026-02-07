"""Unit tests for AI agent Celery tasks."""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.calculation_agent import CalculationEstimate, ItemEstimate
from app.agents.email_classifier import ClassificationResult


class TestRunEmailClassificationTask:
    """Tests for run_email_classification Celery task."""

    @patch("app.agents.tasks.get_settings")
    @patch("app.agents.tasks.EmailClassifier")
    def test_successful_classification(
        self,
        mock_classifier_class: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test successful email classification."""
        from app.agents.tasks import run_email_classification

        # Mock settings with API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-api-key"
        mock_get_settings.return_value = mock_settings

        # Mock classifier instance and result
        mock_classifier = MagicMock()
        mock_classifier_class.return_value = mock_classifier

        mock_result = ClassificationResult(
            category="poptavka",
            confidence=0.95,
            reasoning="Email obsahuje poptávku na výrobu",
            needs_escalation=False,
        )

        # Mock asyncio.run within the task
        with patch("asyncio.run", return_value=mock_result):
            # Call the underlying function directly (bypass Celery decorator)
            # Create mock self with request.id
            mock_self = MagicMock()
            mock_self.request.id = "task-123"

            result = run_email_classification.run(
                email_id="email-456",
                subject="Poptavka - kolena DN200",
                body="Dobrý den, prosím o cenovou nabídku...",
            )

        # Verify result
        assert result == {
            "category": "poptavka",
            "confidence": 0.95,
            "reasoning": "Email obsahuje poptávku na výrobu",
            "needs_escalation": False,
        }

        # Verify classifier was created with correct API key
        mock_classifier_class.assert_called_once_with(api_key="test-api-key")

    @patch("app.agents.tasks.get_settings")
    def test_missing_api_key(
        self,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test handling of missing API key."""
        from app.agents.tasks import run_email_classification

        # Mock settings without API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = None
        mock_get_settings.return_value = mock_settings

        # Call task
        result = run_email_classification.run(
            email_id="email-456",
            subject="Test",
            body="Test body",
        )

        # Verify error result
        assert result == {
            "category": None,
            "confidence": 0.0,
            "reasoning": "Chybí Anthropic API klíč v konfiguraci.",
            "needs_escalation": True,
        }

    @patch("app.agents.tasks.get_settings")
    @patch("app.agents.tasks.EmailClassifier")
    def test_exception_triggers_retry(
        self,
        mock_classifier_class: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test that exceptions trigger task retry."""
        from app.agents.tasks import run_email_classification

        # Mock settings with API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-api-key"
        mock_get_settings.return_value = mock_settings

        # Mock classifier
        mock_classifier = MagicMock()
        mock_classifier_class.return_value = mock_classifier

        # Mock the task's retry method
        mock_retry = MagicMock(side_effect=Exception("Retry called"))
        with patch.object(run_email_classification, "retry", mock_retry):
            # Mock asyncio.run to raise exception
            with patch("asyncio.run", side_effect=RuntimeError("API error")):
                # Verify retry is called
                with pytest.raises(Exception, match="Retry called"):
                    run_email_classification.run(
                        email_id="email-456",
                        subject="Test",
                        body="Test body",
                    )

        mock_retry.assert_called_once_with(countdown=60)


class TestRunCalculationEstimateTask:
    """Tests for run_calculation_estimate Celery task."""

    @patch("app.agents.tasks.get_settings")
    @patch("app.agents.tasks.CalculationAgent")
    def test_successful_estimate(
        self,
        mock_agent_class: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test successful calculation estimate."""
        from app.agents.tasks import run_calculation_estimate

        # Mock settings with API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-api-key"
        mock_get_settings.return_value = mock_settings

        # Mock agent instance
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        # Mock estimate result
        mock_result = CalculationEstimate(
            material_cost_czk=5000.0,
            labor_hours=10.0,
            labor_cost_czk=8500.0,
            overhead_czk=1000.0,
            margin_percent=25.0,
            total_czk=18125.0,
            breakdown=[
                ItemEstimate(
                    name="Koleno DN200",
                    material_cost_czk=5000.0,
                    labor_hours=10.0,
                    notes="Nerezová ocel, svařování TIG",
                )
            ],
            reasoning="Kalkulace založená na běžných tržních cenách.",
        )

        with patch("asyncio.run", return_value=mock_result):
            # Call task
            result = run_calculation_estimate.run(
                order_id="order-789",
                description="Výroba kolena DN200",
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

        # Verify result
        assert result == {
            "material_cost_czk": 5000.0,
            "labor_hours": 10.0,
            "labor_cost_czk": 8500.0,
            "overhead_czk": 1000.0,
            "margin_percent": 25.0,
            "total_czk": 18125.0,
            "breakdown": [
                {
                    "name": "Koleno DN200",
                    "material_cost_czk": 5000.0,
                    "labor_hours": 10.0,
                    "notes": "Nerezová ocel, svařování TIG",
                }
            ],
            "reasoning": "Kalkulace založená na běžných tržních cenách.",
        }

        # Verify agent was created with correct API key
        mock_agent_class.assert_called_once_with(api_key="test-api-key")

    @patch("app.agents.tasks.get_settings")
    def test_missing_api_key(
        self,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test handling of missing API key."""
        from app.agents.tasks import run_calculation_estimate

        # Mock settings without API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = None
        mock_get_settings.return_value = mock_settings

        # Call task
        result = run_calculation_estimate.run(
            order_id="order-789",
            description="Test",
            items=[],
        )

        # Verify error result
        assert result == {
            "material_cost_czk": 0.0,
            "labor_hours": 0.0,
            "labor_cost_czk": 0.0,
            "overhead_czk": 0.0,
            "margin_percent": 0.0,
            "total_czk": 0.0,
            "breakdown": [],
            "reasoning": "Chybí Anthropic API klíč v konfiguraci.",
        }

    @patch("app.agents.tasks.get_settings")
    @patch("app.agents.tasks.CalculationAgent")
    def test_exception_triggers_retry(
        self,
        mock_agent_class: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test that exceptions trigger task retry."""
        from app.agents.tasks import run_calculation_estimate

        # Mock settings with API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-api-key"
        mock_get_settings.return_value = mock_settings

        # Mock agent
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        # Mock the task's retry method
        mock_retry = MagicMock(side_effect=Exception("Retry called"))
        with patch.object(run_calculation_estimate, "retry", mock_retry):
            # Mock asyncio.run to raise exception
            with patch("asyncio.run", side_effect=RuntimeError("API error")):
                # Verify retry is called
                with pytest.raises(Exception, match="Retry called"):
                    run_calculation_estimate.run(
                        order_id="order-789",
                        description="Test",
                        items=[],
                    )

        mock_retry.assert_called_once_with(countdown=60)

    @patch("app.agents.tasks.get_settings")
    @patch("app.agents.tasks.CalculationAgent")
    def test_empty_breakdown_serialization(
        self,
        mock_agent_class: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test serialization with empty breakdown list."""
        from app.agents.tasks import run_calculation_estimate

        # Mock settings with API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-api-key"
        mock_get_settings.return_value = mock_settings

        # Mock agent
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        # Mock result with empty breakdown
        mock_result = CalculationEstimate(
            material_cost_czk=0.0,
            labor_hours=0.0,
            labor_cost_czk=0.0,
            overhead_czk=0.0,
            margin_percent=0.0,
            total_czk=0.0,
            breakdown=[],
            reasoning="Prázdná kalkulace",
        )

        with patch("asyncio.run", return_value=mock_result):
            # Call task
            result = run_calculation_estimate.run(
                order_id="order-789",
                description="Test",
                items=[],
            )

        # Verify empty breakdown
        assert result["breakdown"] == []

    @patch("app.agents.tasks.get_settings")
    @patch("app.agents.tasks.CalculationAgent")
    def test_multiple_items_in_breakdown(
        self,
        mock_agent_class: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test serialization with multiple items in breakdown."""
        from app.agents.tasks import run_calculation_estimate

        # Mock settings with API key
        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = "test-api-key"
        mock_get_settings.return_value = mock_settings

        # Mock agent
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        # Mock result with multiple items
        mock_result = CalculationEstimate(
            material_cost_czk=10000.0,
            labor_hours=20.0,
            labor_cost_czk=17000.0,
            overhead_czk=2000.0,
            margin_percent=30.0,
            total_czk=37700.0,
            breakdown=[
                ItemEstimate(
                    name="Item 1",
                    material_cost_czk=5000.0,
                    labor_hours=10.0,
                    notes="Notes 1",
                ),
                ItemEstimate(
                    name="Item 2",
                    material_cost_czk=5000.0,
                    labor_hours=10.0,
                    notes="Notes 2",
                ),
            ],
            reasoning="Multiple items",
        )

        with patch("asyncio.run", return_value=mock_result):
            # Call task
            result = run_calculation_estimate.run(
                order_id="order-789",
                description="Test",
                items=[],
            )

        # Verify breakdown serialization
        assert len(result["breakdown"]) == 2
        assert result["breakdown"][0] == {
            "name": "Item 1",
            "material_cost_czk": 5000.0,
            "labor_hours": 10.0,
            "notes": "Notes 1",
        }
        assert result["breakdown"][1] == {
            "name": "Item 2",
            "material_cost_czk": 5000.0,
            "labor_hours": 10.0,
            "notes": "Notes 2",
        }
