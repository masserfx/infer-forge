"""Unit tests for email classifier agent (mocked API)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.email_classifier import (
    ClassificationResult,
    EmailClassifier,
)


def _make_tool_use_block(
    category: str = "poptavka",
    confidence: float = 0.95,
    reasoning: str = "Test reasoning",
) -> MagicMock:
    """Create a mock tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = "classify_email"
    block.input = {
        "category": category,
        "confidence": confidence,
        "reasoning": reasoning,
    }
    return block


def _make_response(blocks: list) -> MagicMock:
    """Create a mock API response."""
    response = MagicMock()
    response.content = blocks
    return response


class TestClassificationResult:
    """Tests for ClassificationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ClassificationResult(
            category="poptavka",
            confidence=0.95,
            reasoning="Email obsahuje poptavku",
        )
        assert result.category == "poptavka"
        assert result.confidence == 0.95
        assert result.needs_escalation is False

    def test_escalation_flag(self) -> None:
        """Test escalation flag when explicitly set."""
        result = ClassificationResult(
            category="dotaz",
            confidence=0.5,
            reasoning="Low confidence",
            needs_escalation=True,
        )
        assert result.needs_escalation is True

    def test_confidence_clamping(self) -> None:
        """Test that out-of-range confidence is clamped."""
        result = ClassificationResult(
            category="poptavka",
            confidence=1.5,
            reasoning="Over max",
        )
        assert result.confidence == 1.0

        result2 = ClassificationResult(
            category="poptavka",
            confidence=-0.5,
            reasoning="Under min",
        )
        assert result2.confidence == 0.0

    def test_none_category(self) -> None:
        """Test result with None category."""
        result = ClassificationResult(
            category=None,
            confidence=0.0,
            reasoning="Failed",
            needs_escalation=True,
        )
        assert result.category is None


class TestEmailClassifier:
    """Tests for EmailClassifier with mocked API."""

    @pytest.fixture
    def classifier(self) -> EmailClassifier:
        """Create classifier with test API key."""
        return EmailClassifier(api_key="test-key")

    async def test_classify_poptavka(self, classifier: EmailClassifier) -> None:
        """Test classifying an inquiry email."""
        mock_response = _make_response(
            [
                _make_tool_use_block("poptavka", 0.95, "Email poptavka na kolena"),
            ]
        )

        with patch.object(
            classifier._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await classifier.classify(
                subject="Poptavka - kolena DN200 PN16",
                body="Dobry den, prosim o cenovou nabidku na 50ks kolen...",
            )

        assert result.category == "poptavka"
        assert result.confidence == 0.95
        assert result.needs_escalation is False

    async def test_classify_reklamace(self, classifier: EmailClassifier) -> None:
        """Test classifying a complaint email."""
        mock_response = _make_response(
            [
                _make_tool_use_block("reklamace", 0.88, "Email obsahuje reklamaci"),
            ]
        )

        with patch.object(
            classifier._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await classifier.classify(
                subject="Reklamace - vadne koleno",
                body="Dobry den, dodane koleno nesplnuje specifikaci...",
            )

        assert result.category == "reklamace"
        assert result.confidence == 0.88
        assert result.needs_escalation is False

    async def test_classify_low_confidence_escalation(self, classifier: EmailClassifier) -> None:
        """Test that low confidence triggers escalation."""
        mock_response = _make_response(
            [
                _make_tool_use_block("dotaz", 0.6, "Nejasny email"),
            ]
        )

        with patch.object(
            classifier._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await classifier.classify(
                subject="RE: Informace",
                body="Dekuji za odpoved...",
            )

        assert result.category == "dotaz"
        assert result.confidence == 0.6
        assert result.needs_escalation is True

    async def test_classify_timeout(self, classifier: EmailClassifier) -> None:
        """Test handling of API timeout."""
        with patch.object(
            classifier._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=TimeoutError("Request timed out"),
        ):
            result = await classifier.classify(
                subject="Test",
                body="Test body",
            )

        assert result.category is None
        assert result.confidence == 0.0
        assert result.needs_escalation is True
        assert "vyprseni" in result.reasoning.lower() or "timeout" in result.reasoning.lower()

    async def test_classify_api_error(self, classifier: EmailClassifier) -> None:
        """Test handling of generic API error."""
        with patch.object(
            classifier._client.messages,
            "create",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API error"),
        ):
            result = await classifier.classify(
                subject="Test",
                body="Test body",
            )

        assert result.category is None
        assert result.confidence == 0.0
        assert result.needs_escalation is True

    async def test_classify_no_tool_use_block(self, classifier: EmailClassifier) -> None:
        """Test handling of response without tool_use block."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Some text response"
        mock_response = _make_response([text_block])

        with patch.object(
            classifier._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await classifier.classify(
                subject="Test",
                body="Test body",
            )

        assert result.category is None
        assert result.needs_escalation is True

    async def test_classify_invalid_category(self, classifier: EmailClassifier) -> None:
        """Test handling of invalid category from API."""
        mock_response = _make_response(
            [
                _make_tool_use_block("invalid_category", 0.9, "Invalid"),
            ]
        )

        with patch.object(
            classifier._client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await classifier.classify(
                subject="Test",
                body="Test body",
            )

        assert result.category is None
        assert result.needs_escalation is True

    def test_build_user_message(self) -> None:
        """Test user message construction."""
        msg = EmailClassifier._build_user_message(
            subject="Poptavka",
            body="Kratky text",
        )
        assert "Poptavka" in msg
        assert "Kratky text" in msg

    def test_build_user_message_truncation(self) -> None:
        """Test that long body is truncated."""
        long_body = "x" * 5000
        msg = EmailClassifier._build_user_message("Test", long_body)
        assert "[... text zkracen ...]" in msg
