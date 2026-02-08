"""Pydantic schemas for technical drawing analysis API responses."""

from pydantic import BaseModel, Field


class DrawingDimensionSchema(BaseModel):
    """Dimension extracted from a technical drawing.

    Attributes:
        type: Dimension type (DN, PN, průměr, tloušťka, délka, etc.).
        value: Numeric value of the dimension.
        unit: Unit of measurement (mm, m, DN, PN, bar, etc.).
        tolerance: Optional tolerance specification (±0.5, H7, etc.).
    """

    type: str = Field(..., description="Typ rozměru (DN, PN, průměr, délka, atd.)")
    value: float = Field(..., description="Číselná hodnota rozměru")
    unit: str = Field(..., description="Jednotka (mm, m, DN, PN, bar)")
    tolerance: str | None = Field(None, description="Tolerance (±0.5, H7, f8)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "DN",
                "value": 200,
                "unit": "DN",
                "tolerance": None,
            }
        }


class DrawingMaterialSchema(BaseModel):
    """Material specification extracted from a technical drawing.

    Attributes:
        grade: Material grade designation (P235GH, 1.4301, 11 353, etc.).
        standard: Optional material standard (EN, ČSN, DIN, AISI, etc.).
        type: Optional steel type description (uhlíková, nerezová, etc.).
    """

    grade: str = Field(..., description="Označení materiálu (P235GH, 1.4301, 11 353)")
    standard: str | None = Field(None, description="Norma (EN, ČSN, DIN, AISI)")
    type: str | None = Field(None, description="Typ oceli (uhlíková, nerezová)")

    class Config:
        json_schema_extra = {
            "example": {
                "grade": "P235GH",
                "standard": "EN",
                "type": "uhlíková ocel",
            }
        }


class DrawingToleranceSchema(BaseModel):
    """Tolerance or precision requirement from a technical drawing.

    Attributes:
        type: Tolerance type (rozměrová, geometrická, drsnost).
        value: Tolerance value string (ISO 2768-m, Ra 3.2, ⊥0.05, etc.).
        standard: Optional tolerance standard (ISO 2768, ISO 1101, etc.).
    """

    type: str = Field(..., description="Typ tolerance (rozměrová, geometrická, drsnost)")
    value: str = Field(..., description="Hodnota tolerance (ISO 2768-m, Ra 3.2)")
    standard: str | None = Field(None, description="Norma (ISO 2768, ISO 1101)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "geometrická",
                "value": "⊥0.05",
                "standard": "ISO 1101",
            }
        }


class WeldingRequirementsSchema(BaseModel):
    """Welding requirements and NDT control specifications.

    Attributes:
        wps: Optional WPS (Welding Procedure Specification) reference.
        wpqr: Optional WPQR (Welding Procedure Qualification Record) reference.
        ndt_methods: List of NDT methods (RT, UT, MT, PT, VT, etc.).
        acceptance_criteria: Optional acceptance criteria (EN ISO 5817-B, etc.).
    """

    wps: str | None = Field(None, description="WPS číslo/reference")
    wpqr: str | None = Field(None, description="WPQR číslo/reference")
    ndt_methods: list[str] = Field(
        default_factory=list,
        description="NDT metody (RT, UT, MT, PT, VT)",
    )
    acceptance_criteria: str | None = Field(
        None,
        description="Kritéria přejímky (EN ISO 5817-B)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "wps": "WPS-001-2024",
                "wpqr": None,
                "ndt_methods": ["RT 100%", "MT"],
                "acceptance_criteria": "EN ISO 5817-B",
            }
        }


class DrawingAnalysisResponse(BaseModel):
    """Complete structured analysis result from a technical drawing.

    Attributes:
        dimensions: List of dimensions (DN, PN, průměr, délka, etc.).
        materials: List of material specifications with grades and standards.
        tolerances: List of tolerance requirements.
        surface_treatments: List of surface treatment descriptions.
        welding_requirements: Welding and NDT control requirements.
        notes: Additional technical notes and requirements.
    """

    dimensions: list[DrawingDimensionSchema] = Field(
        default_factory=list,
        description="Rozměry (DN, PN, průměr, délka)",
    )
    materials: list[DrawingMaterialSchema] = Field(
        default_factory=list,
        description="Materiály s normami",
    )
    tolerances: list[DrawingToleranceSchema] = Field(
        default_factory=list,
        description="Tolerance a přesnost",
    )
    surface_treatments: list[str] = Field(
        default_factory=list,
        description="Povrchové úpravy",
    )
    welding_requirements: WeldingRequirementsSchema = Field(
        default_factory=WeldingRequirementsSchema,
        description="Svařovací požadavky",
    )
    notes: str | None = Field(None, description="Další technické poznámky")

    class Config:
        json_schema_extra = {
            "example": {
                "dimensions": [
                    {"type": "DN", "value": 200, "unit": "DN", "tolerance": None},
                    {"type": "PN", "value": 16, "unit": "PN", "tolerance": None},
                    {"type": "tloušťka", "value": 6.3, "unit": "mm", "tolerance": "±0.5"},
                ],
                "materials": [
                    {"grade": "P235GH", "standard": "EN", "type": "uhlíková ocel"}
                ],
                "tolerances": [
                    {"type": "rozměrová", "value": "ISO 2768-m", "standard": "ISO 2768"}
                ],
                "surface_treatments": ["žárové zinkování", "tryskání Sa 2.5"],
                "welding_requirements": {
                    "wps": "WPS-001-2024",
                    "wpqr": None,
                    "ndt_methods": ["RT 100%", "MT"],
                    "acceptance_criteria": "EN ISO 5817-B",
                },
                "notes": "Atestace EN 10204 3.1 požadována",
            }
        }
