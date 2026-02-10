"""Drawing analysis agent for extracting structured data from technical drawings.

Uses Anthropic Claude API with structured tool_use output to extract
dimensions, materials, tolerances, surface treatments, and welding requirements
from OCR text of technical drawings in the steel fabrication domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog
from anthropic import AsyncAnthropic

logger = structlog.get_logger(__name__)

# Anthropic model — centralized in Settings
from app.core.config import get_settings as _get_settings
_MODEL: str = _get_settings().ANTHROPIC_MODEL

# Maximum tokens for the analysis response
_MAX_TOKENS: int = 4096

# Timeout in seconds for the API call
_TIMEOUT_SECONDS: float = 90.0

# Tool definition for structured drawing analysis output
_ANALYZE_TOOL: dict[str, object] = {
    "name": "analyze_drawing",
    "description": (
        "Analyzuj technický výkres a extrahuj strukturovaná data: "
        "rozměry (DN, PN, průměr, tloušťka, délka), materiály (dle norem EN/ČSN/DIN), "
        "tolerance (rozměrové, geometrické, drsnost), povrchové úpravy, "
        "svařovací požadavky (WPS, WPQR, NDT metody). "
        "Pokud některá informace není ve výkresu uvedena, vrať null/prázdné pole."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "dimensions": {
                "type": "array",
                "description": "Seznam rozměrů nalezených ve výkresu.",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": (
                                "Typ rozměru: DN (jmenovitý průměr), PN (jmenovitý tlak), "
                                "průměr, tloušťka, délka, výška, šířka."
                            ),
                        },
                        "value": {
                            "type": "number",
                            "description": "Číselná hodnota rozměru.",
                        },
                        "unit": {
                            "type": "string",
                            "description": "Jednotka: mm, m, DN, PN, bar atd.",
                        },
                        "tolerance": {
                            "type": ["string", "null"],
                            "description": "Tolerance rozměru (např. ±0.5, +0.2/-0.1, H7, f8).",
                        },
                    },
                    "required": ["type", "value", "unit"],
                },
            },
            "materials": {
                "type": "array",
                "description": "Seznam materiálů specifikovaných ve výkresu.",
                "items": {
                    "type": "object",
                    "properties": {
                        "grade": {
                            "type": "string",
                            "description": (
                                "Označení materiálu: P235GH, S235JR, S355J2, "
                                "11 353, 12 022, 1.4301, 1.4307, 1.4541, "
                                "AISI 304, AISI 316L atd."
                            ),
                        },
                        "standard": {
                            "type": ["string", "null"],
                            "description": "Norma materiálu: EN, ČSN, DIN, ASTM, AISI.",
                        },
                        "type": {
                            "type": ["string", "null"],
                            "description": (
                                "Typ oceli: uhlíková, nízkolegovaná, nerezová, "
                                "konstrukční, tlakově náročná."
                            ),
                        },
                    },
                    "required": ["grade"],
                },
            },
            "tolerances": {
                "type": "array",
                "description": "Tolerance a požadavky na přesnost.",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": (
                                "Typ tolerance: rozměrová (ISO 2768), geometrická (kolmost, "
                                "rovnoběžnost, rovinnost), drsnost povrchu (Ra, Rz)."
                            ),
                        },
                        "value": {
                            "type": "string",
                            "description": (
                                "Hodnota tolerance: ISO 2768-m, Ra 3.2, Rz 12.5, "
                                "⊥0.05, //0.1 atd."
                            ),
                        },
                        "standard": {
                            "type": ["string", "null"],
                            "description": "Norma tolerance: ISO 2768, ISO 1101, ISO 4287 atd.",
                        },
                    },
                    "required": ["type", "value"],
                },
            },
            "surface_treatments": {
                "type": "array",
                "description": "Povrchové úpravy a ochrany.",
                "items": {
                    "type": "string",
                    "description": (
                        "Povrchová úprava: žárové zinkování, tryskání (Sa 2.5, Sa 3), "
                        "nátěr (barva, tloušťka), pasivace, chemická oxidace, "
                        "pozinkování, chromování atd."
                    ),
                },
            },
            "welding_requirements": {
                "type": "object",
                "description": "Svařovací požadavky a kontrola.",
                "properties": {
                    "wps": {
                        "type": ["string", "null"],
                        "description": (
                            "Číslo nebo reference WPS (Welding Procedure Specification)."
                        ),
                    },
                    "wpqr": {
                        "type": ["string", "null"],
                        "description": (
                            "Číslo nebo reference WPQR (Welding Procedure Qualification Record)."
                        ),
                    },
                    "ndt_methods": {
                        "type": "array",
                        "description": "NDT metody kontroly svárů.",
                        "items": {
                            "type": "string",
                            "description": (
                                "Metoda NDT: RT (radiografie), UT (ultrazvuk), "
                                "MT (magnetická prášková), PT (kapilární), "
                                "VT (vizuální), 100% kontrola."
                            ),
                        },
                    },
                    "acceptance_criteria": {
                        "type": ["string", "null"],
                        "description": (
                            "Kritéria přejímky svárů: EN ISO 5817-B, EN ISO 5817-C, "
                            "úroveň kvality atd."
                        ),
                    },
                },
            },
            "notes": {
                "type": ["string", "null"],
                "description": (
                    "Další technické poznámky a požadavky: atesty EN 10204 3.1, "
                    "tlakové zkoušky, montážní požadavky, balení, značení atd."
                ),
            },
        },
        "required": [
            "dimensions",
            "materials",
            "tolerances",
            "surface_treatments",
            "welding_requirements",
            "notes",
        ],
    },
}

# System prompt for the drawing analysis task
_SYSTEM_PROMPT: str = """Jsi AI asistent strojírenské firmy Infer s.r.o., která vyrábí potrubní díly,
svařence a ocelové konstrukce.

Tvým úkolem je analyzovat text extrahovaný z technického výkresu (OCR output) a extrahovat
strukturovaná data:

**ROZMĚRY:**
- DN (jmenovitý průměr potrubí): DN100, DN200, DN500
- PN (jmenovitý tlak): PN10, PN16, PN25, PN40
- Průměr × tloušťka stěny: 219.1×6.3 mm, 273×8 mm
- Délky, výšky, šířky v mm nebo m
- Tolerance: ±0.5, +0.2/-0.1, H7, f8, IT8

**MATERIÁLY:**
Rozlišuj normy:
- ČSN: 11 353, 12 022, 11 375, 11 523
- EN: P235GH, S235JR, S355J2, S355J2H, P265GH, P355GH
- DIN/číselné: 1.4301, 1.4307, 1.4541, 1.4571 (nerez)
- AISI: 304, 316L, 321
Typy: uhlíková ocel, nízkolegovaná, nerezová (austentická, feritická),
konstrukční, pro tlakové nádoby.

**TOLERANCE:**
- Obecné: ISO 2768-m, ISO 2768-f
- Geometrické (ISO 1101): kolmost ⊥, rovnoběžnost //, rovinnost, soustřednost
- Drsnost povrchu (ISO 4287): Ra 3.2, Ra 6.3, Rz 12.5

**POVRCHOVÉ ÚPRAVY:**
- Žárové zinkování (hot-dip galvanizing)
- Tryskání: Sa 2.5, Sa 3 (dle ISO 8501-1)
- Nátěry: barva, tloušťka vrstvy (µm)
- Pasivace (nerez), chromování, fosfátování
- Pozinkování elektrolytické

**SVAŘOVACÍ POŽADAVKY:**
- WPS (Welding Procedure Specification) - číslo postupu
- WPQR (Welding Procedure Qualification Record)
- NDT metody:
  - RT: radiografie (rentgen)
  - UT: ultrazvuková kontrola
  - MT: magnetická prášková kontrola
  - PT: kapilární kontrola
  - VT: vizuální kontrola
- Kritéria přejímky: EN ISO 5817 (úroveň B, C, D)

**DALŠÍ POŽADAVKY:**
- Atestace: EN 10204 3.1, 3.2 (materiálové certifikáty)
- Tlakové zkoušky: zkušební tlak, medium
- Značení, balení, doprava

DŮLEŽITÉ:
- Pokud informace ve výkresu není, vrať null nebo prázdné pole
- Zachovej původní označení a formát rozměrů
- Rozlišuj různé normy materiálů (EN vs ČSN vs DIN)
- U NDT uveď kompletní požadavek (např. "RT 100%", "UT + MT")

Použij nástroj analyze_drawing pro vrácení strukturovaného výsledku."""


@dataclass(frozen=True, slots=True)
class DrawingDimension:
    """A dimension extracted from a technical drawing.

    Attributes:
        type: Dimension type (DN, PN, průměr, tloušťka, délka, etc.).
        value: Numeric value of the dimension.
        unit: Unit of measurement (mm, m, DN, PN, bar, etc.).
        tolerance: Optional tolerance specification (±0.5, H7, etc.).
    """

    type: str
    value: float
    unit: str
    tolerance: str | None = None


@dataclass(frozen=True, slots=True)
class DrawingMaterial:
    """A material specification extracted from a technical drawing.

    Attributes:
        grade: Material grade designation (P235GH, 1.4301, 11 353, etc.).
        standard: Optional material standard (EN, ČSN, DIN, AISI, etc.).
        type: Optional steel type description (uhlíková, nerezová, etc.).
    """

    grade: str
    standard: str | None = None
    type: str | None = None


@dataclass(frozen=True, slots=True)
class DrawingTolerance:
    """A tolerance or precision requirement from a technical drawing.

    Attributes:
        type: Tolerance type (rozměrová, geometrická, drsnost).
        value: Tolerance value string (ISO 2768-m, Ra 3.2, ⊥0.05, etc.).
        standard: Optional tolerance standard (ISO 2768, ISO 1101, etc.).
    """

    type: str
    value: str
    standard: str | None = None


@dataclass(frozen=True, slots=True)
class WeldingRequirements:
    """Welding requirements and NDT control specifications.

    Attributes:
        wps: Optional WPS (Welding Procedure Specification) reference.
        wpqr: Optional WPQR (Welding Procedure Qualification Record) reference.
        ndt_methods: List of NDT methods (RT, UT, MT, PT, VT, etc.).
        acceptance_criteria: Optional acceptance criteria (EN ISO 5817-B, etc.).
    """

    wps: str | None = None
    wpqr: str | None = None
    ndt_methods: list[str] = field(default_factory=list)
    acceptance_criteria: str | None = None


@dataclass(frozen=True, slots=True)
class DrawingAnalysis:
    """Complete structured analysis result from a technical drawing.

    Attributes:
        dimensions: List of dimensions (DN, PN, průměr, délka, etc.).
        materials: List of material specifications with grades and standards.
        tolerances: List of tolerance requirements.
        surface_treatments: List of surface treatment descriptions.
        welding_requirements: Welding and NDT control requirements.
        notes: Additional technical notes and requirements.
    """

    dimensions: list[DrawingDimension] = field(default_factory=list)
    materials: list[DrawingMaterial] = field(default_factory=list)
    tolerances: list[DrawingTolerance] = field(default_factory=list)
    surface_treatments: list[str] = field(default_factory=list)
    welding_requirements: WeldingRequirements = field(default_factory=WeldingRequirements)
    notes: str | None = None


class DrawingAnalyzer:
    """Extracts structured data from technical drawing OCR text.

    Uses Anthropic Claude API with tool_use to reliably extract dimensions,
    materials, tolerances, surface treatments, and welding requirements
    from OCR text of technical drawings for steel fabrication projects.

    Args:
        api_key: Anthropic API key for authentication.

    Example:
        >>> analyzer = DrawingAnalyzer(api_key="sk-ant-...")
        >>> result = await analyzer.analyze(
        ...     ocr_text="DN200 PN16, material P235GH, žárové zinkování...",
        ... )
        >>> result.dimensions[0].type
        'DN'
        >>> result.materials[0].grade
        'P235GH'
    """

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def analyze(self, ocr_text: str) -> DrawingAnalysis:
        """Analyze OCR text from a technical drawing.

        Args:
            ocr_text: Raw text extracted from the technical drawing via OCR.

        Returns:
            DrawingAnalysis with extracted structured data.
            Returns an empty DrawingAnalysis on failure.
        """
        if not ocr_text or not ocr_text.strip():
            logger.warning("drawing_analysis.empty_text")
            return DrawingAnalysis()

        log = logger.bind(text_length=len(ocr_text))
        log.info("drawing_analysis.started")

        user_message = self._build_user_message(ocr_text)

        try:
            response = await self._client.messages.create(  # type: ignore[call-overload]
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                tools=[_ANALYZE_TOOL],
                tool_choice={"type": "tool", "name": "analyze_drawing"},
                messages=[{"role": "user", "content": user_message}],
                timeout=_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            log.warning("drawing_analysis.timeout")
            return DrawingAnalysis()
        except Exception:
            log.exception("drawing_analysis.api_error")
            return DrawingAnalysis()

        return self._parse_response(response, log)

    @staticmethod
    def _build_user_message(ocr_text: str) -> str:
        """Build the user message from OCR text.

        Args:
            ocr_text: Raw OCR text from the technical drawing.

        Returns:
            Formatted user message string.
        """
        # Limit text to 8000 characters to stay within token limits
        truncated_text = ocr_text[:8000]
        if len(ocr_text) > 8000:
            truncated_text += "\n\n[... text zkrácen ...]"

        return (
            f"Analyzuj následující text extrahovaný z technického výkresu "
            f"a extrahuj strukturovaná data:\n\n{truncated_text}"
        )

    @staticmethod
    def _parse_response(
        response: object,
        log: structlog.stdlib.BoundLogger,
    ) -> DrawingAnalysis:
        """Parse the Anthropic API response into DrawingAnalysis.

        Args:
            response: The raw API response from Anthropic.
            log: Bound structlog logger for contextual logging.

        Returns:
            Parsed DrawingAnalysis, or empty DrawingAnalysis on parse failure.
        """
        # Extract tool_use block from response content
        tool_input: dict[str, object] | None = None
        for block in response.content:  # type: ignore[attr-defined]
            if block.type == "tool_use" and block.name == "analyze_drawing":
                tool_input = block.input
                break

        if tool_input is None:
            log.error(
                "drawing_analysis.no_tool_use_block",
                response_content=str(response.content),  # type: ignore[attr-defined]
            )
            return DrawingAnalysis()

        # Parse dimensions
        dimensions: list[DrawingDimension] = []
        raw_dimensions = tool_input.get("dimensions", [])
        if isinstance(raw_dimensions, list):
            for raw_dim in raw_dimensions:
                if not isinstance(raw_dim, dict):
                    continue
                dim_type = raw_dim.get("type")
                dim_value = raw_dim.get("value")
                dim_unit = raw_dim.get("unit")
                if not all([dim_type, dim_unit]) or dim_value is None:
                    continue

                try:
                    dimensions.append(
                        DrawingDimension(
                            type=str(dim_type),
                            value=float(dim_value),
                            unit=str(dim_unit),
                            tolerance=_str_or_none(raw_dim.get("tolerance")),
                        )
                    )
                except (TypeError, ValueError):
                    continue

        # Parse materials
        materials: list[DrawingMaterial] = []
        raw_materials = tool_input.get("materials", [])
        if isinstance(raw_materials, list):
            for raw_mat in raw_materials:
                if not isinstance(raw_mat, dict):
                    continue
                grade = raw_mat.get("grade")
                if not grade or not isinstance(grade, str):
                    continue

                materials.append(
                    DrawingMaterial(
                        grade=grade,
                        standard=_str_or_none(raw_mat.get("standard")),
                        type=_str_or_none(raw_mat.get("type")),
                    )
                )

        # Parse tolerances
        tolerances: list[DrawingTolerance] = []
        raw_tolerances = tool_input.get("tolerances", [])
        if isinstance(raw_tolerances, list):
            for raw_tol in raw_tolerances:
                if not isinstance(raw_tol, dict):
                    continue
                tol_type = raw_tol.get("type")
                tol_value = raw_tol.get("value")
                if not tol_type or not tol_value:
                    continue

                tolerances.append(
                    DrawingTolerance(
                        type=str(tol_type),
                        value=str(tol_value),
                        standard=_str_or_none(raw_tol.get("standard")),
                    )
                )

        # Parse surface treatments
        surface_treatments: list[str] = []
        raw_treatments = tool_input.get("surface_treatments", [])
        if isinstance(raw_treatments, list):
            for treatment in raw_treatments:
                if isinstance(treatment, str) and treatment.strip():
                    surface_treatments.append(treatment.strip())

        # Parse welding requirements
        raw_welding = tool_input.get("welding_requirements", {})
        ndt_methods: list[str] = []
        if isinstance(raw_welding, dict):
            raw_ndt = raw_welding.get("ndt_methods", [])
            if isinstance(raw_ndt, list):
                for method in raw_ndt:
                    if isinstance(method, str) and method.strip():
                        ndt_methods.append(method.strip())

            welding_requirements = WeldingRequirements(
                wps=_str_or_none(raw_welding.get("wps")),
                wpqr=_str_or_none(raw_welding.get("wpqr")),
                ndt_methods=ndt_methods,
                acceptance_criteria=_str_or_none(raw_welding.get("acceptance_criteria")),
            )
        else:
            welding_requirements = WeldingRequirements()

        result = DrawingAnalysis(
            dimensions=dimensions,
            materials=materials,
            tolerances=tolerances,
            surface_treatments=surface_treatments,
            welding_requirements=welding_requirements,
            notes=_str_or_none(tool_input.get("notes")),
        )

        log.info(
            "drawing_analysis.completed",
            dimensions_count=len(result.dimensions),
            materials_count=len(result.materials),
            tolerances_count=len(result.tolerances),
            surface_treatments_count=len(result.surface_treatments),
            has_welding_requirements=bool(
                result.welding_requirements.wps
                or result.welding_requirements.wpqr
                or result.welding_requirements.ndt_methods
            ),
        )

        return result


def _str_or_none(value: object) -> str | None:
    """Convert a value to string, returning None for empty/null values.

    Args:
        value: Any value from the parsed tool output.

    Returns:
        The string representation, or None if the value is falsy.
    """
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None
