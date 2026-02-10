"""Tests for DrawingAnalyzer - technical drawing AI analysis."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.ocr.drawing_analyzer import DrawingAnalysis, DrawingAnalyzer


class MockToolUseBlock:
    """Mock tool_use block from Anthropic API response."""

    def __init__(self, input_data: dict[str, object]) -> None:
        self.type = "tool_use"
        self.name = "analyze_drawing"
        self.input = input_data


class MockResponse:
    """Mock Anthropic API response."""

    def __init__(self, tool_input: dict[str, object]) -> None:
        self.content = [MockToolUseBlock(tool_input)]


@pytest.fixture
def mock_anthropic_client() -> AsyncMock:
    """Create a mock Anthropic client."""
    return AsyncMock()


@pytest.fixture
def drawing_analyzer(mock_anthropic_client: AsyncMock) -> DrawingAnalyzer:
    """Create DrawingAnalyzer with mocked Anthropic client."""
    analyzer = DrawingAnalyzer(api_key="test-key")
    analyzer._client = mock_anthropic_client
    return analyzer


@pytest.mark.asyncio
async def test_analyze_drawing_success(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test successful drawing analysis with complete data."""
    ocr_text = """
    VÝKRES Č. 001-2024
    DN200 PN16
    Materiál: P235GH dle EN 10028-2
    Tloušťka stěny: 6.3 mm ±0.5
    Tolerance: ISO 2768-m
    Povrchová úprava: žárové zinkování
    WPS: WPS-001-2024
    NDT: RT 100%, MT
    Kritéria přejímky: EN ISO 5817-B
    Atestace: EN 10204 3.1
    """

    mock_response = MockResponse(
        {
            "dimensions": [
                {"type": "DN", "value": 200, "unit": "DN", "tolerance": None},
                {"type": "PN", "value": 16, "unit": "PN", "tolerance": None},
                {"type": "tloušťka", "value": 6.3, "unit": "mm", "tolerance": "±0.5"},
            ],
            "materials": [
                {
                    "grade": "P235GH",
                    "standard": "EN 10028-2",
                    "type": "uhlíková ocel",
                }
            ],
            "tolerances": [
                {"type": "rozměrová", "value": "ISO 2768-m", "standard": "ISO 2768"}
            ],
            "surface_treatments": ["žárové zinkování"],
            "welding_requirements": {
                "wps": "WPS-001-2024",
                "wpqr": None,
                "ndt_methods": ["RT 100%", "MT"],
                "acceptance_criteria": "EN ISO 5817-B",
            },
            "notes": "Atestace EN 10204 3.1 požadována",
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze(ocr_text)

    # Verify API call
    mock_anthropic_client.messages.create.assert_called_once()
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    from app.core.config import get_settings
    assert call_kwargs["model"] == get_settings().ANTHROPIC_MODEL
    assert "analyze_drawing" in str(call_kwargs["tool_choice"])

    # Verify dimensions
    assert len(result.dimensions) == 3
    assert result.dimensions[0].type == "DN"
    assert result.dimensions[0].value == 200
    assert result.dimensions[0].unit == "DN"
    assert result.dimensions[0].tolerance is None

    assert result.dimensions[2].type == "tloušťka"
    assert result.dimensions[2].value == 6.3
    assert result.dimensions[2].tolerance == "±0.5"

    # Verify materials
    assert len(result.materials) == 1
    assert result.materials[0].grade == "P235GH"
    assert result.materials[0].standard == "EN 10028-2"
    assert result.materials[0].type == "uhlíková ocel"

    # Verify tolerances
    assert len(result.tolerances) == 1
    assert result.tolerances[0].type == "rozměrová"
    assert result.tolerances[0].value == "ISO 2768-m"

    # Verify surface treatments
    assert len(result.surface_treatments) == 1
    assert result.surface_treatments[0] == "žárové zinkování"

    # Verify welding requirements
    assert result.welding_requirements.wps == "WPS-001-2024"
    assert result.welding_requirements.wpqr is None
    assert len(result.welding_requirements.ndt_methods) == 2
    assert "RT 100%" in result.welding_requirements.ndt_methods
    assert result.welding_requirements.acceptance_criteria == "EN ISO 5817-B"

    # Verify notes
    assert result.notes == "Atestace EN 10204 3.1 požadována"


@pytest.mark.asyncio
async def test_analyze_empty_text(drawing_analyzer: DrawingAnalyzer) -> None:
    """Test analysis with empty OCR text."""
    result = await drawing_analyzer.analyze("")

    assert isinstance(result, DrawingAnalysis)
    assert len(result.dimensions) == 0
    assert len(result.materials) == 0
    assert len(result.tolerances) == 0
    assert len(result.surface_treatments) == 0
    assert result.notes is None


@pytest.mark.asyncio
async def test_analyze_whitespace_only_text(drawing_analyzer: DrawingAnalyzer) -> None:
    """Test analysis with whitespace-only text."""
    result = await drawing_analyzer.analyze("   \n\t  \n  ")

    assert isinstance(result, DrawingAnalysis)
    assert len(result.dimensions) == 0
    assert len(result.materials) == 0


@pytest.mark.asyncio
async def test_analyze_api_failure(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test API failure returns empty analysis."""
    mock_anthropic_client.messages.create.side_effect = Exception("API Error")

    result = await drawing_analyzer.analyze("Some drawing text")

    assert isinstance(result, DrawingAnalysis)
    assert len(result.dimensions) == 0
    assert len(result.materials) == 0
    assert len(result.tolerances) == 0


@pytest.mark.asyncio
async def test_analyze_api_timeout(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test API timeout returns empty analysis."""
    mock_anthropic_client.messages.create.side_effect = TimeoutError()

    result = await drawing_analyzer.analyze("Some drawing text")

    assert isinstance(result, DrawingAnalysis)
    assert len(result.dimensions) == 0


@pytest.mark.asyncio
async def test_analyze_extracts_dimensions(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test extraction of various dimension types."""
    mock_response = MockResponse(
        {
            "dimensions": [
                {"type": "DN", "value": 500, "unit": "DN", "tolerance": None},
                {"type": "PN", "value": 40, "unit": "PN", "tolerance": None},
                {"type": "průměr", "value": 273, "unit": "mm", "tolerance": "H7"},
                {"type": "tloušťka", "value": 8.0, "unit": "mm", "tolerance": "±0.3"},
                {"type": "délka", "value": 6000, "unit": "mm", "tolerance": "+5/-0"},
            ],
            "materials": [],
            "tolerances": [],
            "surface_treatments": [],
            "welding_requirements": {},
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze("DN500 PN40 273×8 délka 6000mm")

    assert len(result.dimensions) == 5
    # DN
    assert result.dimensions[0].type == "DN"
    assert result.dimensions[0].value == 500
    # PN
    assert result.dimensions[1].type == "PN"
    assert result.dimensions[1].value == 40
    # Průměr with tolerance
    assert result.dimensions[2].type == "průměr"
    assert result.dimensions[2].value == 273
    assert result.dimensions[2].tolerance == "H7"
    # Tloušťka
    assert result.dimensions[3].type == "tloušťka"
    assert result.dimensions[3].value == 8.0
    # Délka
    assert result.dimensions[4].type == "délka"
    assert result.dimensions[4].value == 6000


@pytest.mark.asyncio
async def test_analyze_extracts_materials(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test extraction of various material standards."""
    mock_response = MockResponse(
        {
            "dimensions": [],
            "materials": [
                {
                    "grade": "P235GH",
                    "standard": "EN",
                    "type": "uhlíková ocel pro tlakové nádoby",
                },
                {"grade": "S355J2", "standard": "EN", "type": "konstrukční ocel"},
                {"grade": "11 353", "standard": "ČSN", "type": "uhlíková ocel"},
                {"grade": "1.4301", "standard": "DIN", "type": "nerezová ocel austentická"},
                {"grade": "AISI 316L", "standard": "AISI", "type": "nerezová ocel"},
            ],
            "tolerances": [],
            "surface_treatments": [],
            "welding_requirements": {},
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze(
        "Materiály: P235GH, S355J2, 11 353, 1.4301, AISI 316L"
    )

    assert len(result.materials) == 5
    # EN standard
    assert result.materials[0].grade == "P235GH"
    assert result.materials[0].standard == "EN"
    assert "tlakové nádoby" in result.materials[0].type
    # ČSN standard
    assert result.materials[2].grade == "11 353"
    assert result.materials[2].standard == "ČSN"
    # DIN standard
    assert result.materials[3].grade == "1.4301"
    assert result.materials[3].standard == "DIN"
    assert "nerezová" in result.materials[3].type
    # AISI standard
    assert result.materials[4].grade == "AISI 316L"
    assert result.materials[4].standard == "AISI"


@pytest.mark.asyncio
async def test_analyze_extracts_surface_treatments(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test extraction of surface treatments."""
    mock_response = MockResponse(
        {
            "dimensions": [],
            "materials": [],
            "tolerances": [],
            "surface_treatments": [
                "žárové zinkování",
                "tryskání Sa 2.5",
                "nátěr epoxidový 120 µm",
                "pasivace",
            ],
            "welding_requirements": {},
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze(
        "Povrchová úprava: žárové zinkování, tryskání Sa 2.5, nátěr, pasivace"
    )

    assert len(result.surface_treatments) == 4
    assert "žárové zinkování" in result.surface_treatments
    assert "tryskání Sa 2.5" in result.surface_treatments
    assert "nátěr epoxidový 120 µm" in result.surface_treatments
    assert "pasivace" in result.surface_treatments


@pytest.mark.asyncio
async def test_analyze_extracts_welding(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test extraction of welding requirements."""
    mock_response = MockResponse(
        {
            "dimensions": [],
            "materials": [],
            "tolerances": [],
            "surface_treatments": [],
            "welding_requirements": {
                "wps": "WPS-INF-001-2024",
                "wpqr": "WPQR-INF-001",
                "ndt_methods": ["RT 100%", "UT", "MT", "VT"],
                "acceptance_criteria": "EN ISO 5817 úroveň B",
            },
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze(
        "WPS-INF-001-2024, WPQR-INF-001, NDT: RT 100%, UT, MT, VT, EN ISO 5817-B"
    )

    assert result.welding_requirements.wps == "WPS-INF-001-2024"
    assert result.welding_requirements.wpqr == "WPQR-INF-001"
    assert len(result.welding_requirements.ndt_methods) == 4
    assert "RT 100%" in result.welding_requirements.ndt_methods
    assert "UT" in result.welding_requirements.ndt_methods
    assert "MT" in result.welding_requirements.ndt_methods
    assert "VT" in result.welding_requirements.ndt_methods
    assert result.welding_requirements.acceptance_criteria == "EN ISO 5817 úroveň B"


@pytest.mark.asyncio
async def test_analyze_no_tool_use_block(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test response without tool_use block returns empty analysis."""

    class MockTextBlock:
        type = "text"
        text = "Some text response"

    mock_response = MagicMock()
    mock_response.content = [MockTextBlock()]
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze("Some text")

    assert isinstance(result, DrawingAnalysis)
    assert len(result.dimensions) == 0
    assert len(result.materials) == 0


@pytest.mark.asyncio
async def test_analyze_invalid_dimension_data(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test handling of invalid dimension data."""
    mock_response = MockResponse(
        {
            "dimensions": [
                {"type": "DN", "value": "invalid", "unit": "DN"},  # Invalid value
                {"type": "PN", "value": 16},  # Missing unit
                {"value": 100, "unit": "mm"},  # Missing type
                {"type": "délka", "value": 500, "unit": "mm"},  # Valid
            ],
            "materials": [],
            "tolerances": [],
            "surface_treatments": [],
            "welding_requirements": {},
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze("Some text")

    # Only the valid dimension should be parsed
    assert len(result.dimensions) == 1
    assert result.dimensions[0].type == "délka"
    assert result.dimensions[0].value == 500


@pytest.mark.asyncio
async def test_analyze_invalid_material_data(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test handling of invalid material data."""
    mock_response = MockResponse(
        {
            "dimensions": [],
            "materials": [
                {},  # Missing grade
                {"grade": ""},  # Empty grade
                {"grade": 123},  # Non-string grade (will be converted)
                {"grade": "P235GH", "standard": "EN"},  # Valid
            ],
            "tolerances": [],
            "surface_treatments": [],
            "welding_requirements": {},
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze("Some text")

    # Only valid materials should be parsed
    assert len(result.materials) == 1
    assert result.materials[0].grade == "P235GH"


@pytest.mark.asyncio
async def test_analyze_empty_welding_requirements(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test handling of empty welding requirements."""
    mock_response = MockResponse(
        {
            "dimensions": [],
            "materials": [],
            "tolerances": [],
            "surface_treatments": [],
            "welding_requirements": {
                "wps": None,
                "wpqr": None,
                "ndt_methods": [],
                "acceptance_criteria": None,
            },
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze("Some text")

    assert result.welding_requirements.wps is None
    assert result.welding_requirements.wpqr is None
    assert len(result.welding_requirements.ndt_methods) == 0
    assert result.welding_requirements.acceptance_criteria is None


@pytest.mark.asyncio
async def test_analyze_long_text_truncation(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test that very long OCR text is truncated."""
    long_text = "A" * 10000  # More than 8000 characters
    mock_response = MockResponse(
        {
            "dimensions": [],
            "materials": [],
            "tolerances": [],
            "surface_treatments": [],
            "welding_requirements": {},
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    await drawing_analyzer.analyze(long_text)

    # Check that the text passed to API was truncated
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    user_message = call_kwargs["messages"][0]["content"]
    assert len(user_message) < len(long_text)
    assert "zkrácen" in user_message  # Czech for "truncated"


@pytest.mark.asyncio
async def test_analyze_tolerances_with_standards(
    drawing_analyzer: DrawingAnalyzer,
    mock_anthropic_client: AsyncMock,
) -> None:
    """Test extraction of tolerances with various standards."""
    mock_response = MockResponse(
        {
            "dimensions": [],
            "materials": [],
            "tolerances": [
                {"type": "rozměrová", "value": "ISO 2768-m", "standard": "ISO 2768"},
                {"type": "geometrická", "value": "⊥0.05", "standard": "ISO 1101"},
                {"type": "drsnost", "value": "Ra 3.2", "standard": "ISO 4287"},
                {"type": "geometrická", "value": "//0.1", "standard": "ISO 1101"},
            ],
            "surface_treatments": [],
            "welding_requirements": {},
            "notes": None,
        }
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = await drawing_analyzer.analyze(
        "Tolerance: ISO 2768-m, ⊥0.05, Ra 3.2, //0.1"
    )

    assert len(result.tolerances) == 4
    # General dimensional tolerance
    assert result.tolerances[0].type == "rozměrová"
    assert result.tolerances[0].value == "ISO 2768-m"
    # Perpendicularity
    assert result.tolerances[1].type == "geometrická"
    assert result.tolerances[1].value == "⊥0.05"
    # Surface roughness
    assert result.tolerances[2].type == "drsnost"
    assert result.tolerances[2].value == "Ra 3.2"
    # Parallelism
    assert result.tolerances[3].value == "//0.1"
