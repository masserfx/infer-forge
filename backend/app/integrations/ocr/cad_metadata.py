"""CAD metadata extraction for DWG/DXF and STEP files.

Extracts metadata from technical drawing files commonly used in manufacturing.
Supports DXF (AutoCAD Exchange Format) and STEP (ISO 10303) formats.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CADMetadata:
    """Metadata extracted from CAD files.

    Attributes:
        file_format: File format identifier (DXF, DWG, STEP).
        layers: List of layer names (DXF/DWG concept).
        blocks: List of block/component names.
        text_entities: List of text content found in drawing.
        dimensions: List of dimension entities (measurements).
        product_name: Product name from STEP PRODUCT entity.
        material: Material designation (e.g., from MATERIAL_DESIGNATION).
        description: Product description.
        protocol_version: STEP protocol version (AP203, AP214, etc.).
        raw_metadata: Raw metadata dictionary for debugging.
    """

    file_format: str
    layers: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    text_entities: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    product_name: str | None = None
    material: str | None = None
    description: str | None = None
    protocol_version: str | None = None
    raw_metadata: dict[str, object] = field(default_factory=dict)


class CADMetadataExtractor:
    """Extracts metadata from DWG/DXF and STEP CAD files.

    Supports:
    - DXF: Full parsing via ezdxf (layers, blocks, text, dimensions)
    - DWG: Limited support (ezdxf requires conversion, returns empty on failure)
    - STEP: Text-based parsing of common entities (PRODUCT, MATERIAL, etc.)
    """

    def __init__(self) -> None:
        """Initialize CAD metadata extractor."""
        self._supported_dxf_types = {".dxf"}
        self._supported_dwg_types = {".dwg"}
        self._supported_step_types = {".stp", ".step"}

    def extract_dwg_metadata(self, file_path: str) -> CADMetadata:
        """Extract metadata from DWG file.

        Note: ezdxf cannot directly open binary DWG files. This method attempts
        to read as DXF (some DWG files may be in DXF format). For true binary
        DWG, returns empty metadata with note in raw_metadata.

        Args:
            file_path: Absolute path to DWG file.

        Returns:
            CADMetadata with extracted data, or empty result on failure.
        """
        path = Path(file_path)

        if not path.exists():
            logger.error("cad_file_not_found", file_path=file_path)
            return CADMetadata(
                file_format="DWG",
                raw_metadata={"error": "File not found"},
            )

        try:
            # Try reading as DXF (some DWG files are actually DXF)
            doc = ezdxf.readfile(file_path)  # type: ignore[attr-defined]
            metadata = self._extract_dxf_entities(doc)
            metadata.file_format = "DWG"

            logger.info(
                "cad_dwg_success",
                file_path=file_path,
                layers=len(metadata.layers),
                blocks=len(metadata.blocks),
                texts=len(metadata.text_entities),
            )

            return metadata

        except ezdxf.DXFError as e:  # type: ignore[attr-defined]
            logger.warning(
                "cad_dwg_unsupported",
                file_path=file_path,
                error=str(e),
                note="Binary DWG files require external conversion to DXF",
            )
            return CADMetadata(
                file_format="DWG",
                raw_metadata={
                    "error": "Binary DWG not supported",
                    "note": "Use AutoCAD or ODA File Converter to convert to DXF",
                    "ezdxf_error": str(e),
                },
            )
        except Exception as e:
            logger.error("cad_dwg_failed", file_path=file_path, error=str(e), exc_info=True)
            return CADMetadata(
                file_format="DWG",
                raw_metadata={"error": str(e)},
            )

    def extract_dxf_metadata(self, file_path: str) -> CADMetadata:
        """Extract metadata from DXF file.

        DXF is a text-based CAD format that ezdxf can fully parse. Extracts:
        - Layer names
        - Block names (reusable components)
        - Text entities (annotations, labels)
        - Dimension entities (measurements)

        Args:
            file_path: Absolute path to DXF file.

        Returns:
            CADMetadata with extracted data, or empty result on failure.
        """
        path = Path(file_path)

        if not path.exists():
            logger.error("cad_file_not_found", file_path=file_path)
            return CADMetadata(
                file_format="DXF",
                raw_metadata={"error": "File not found"},
            )

        try:
            doc = ezdxf.readfile(file_path)  # type: ignore[attr-defined]
            metadata = self._extract_dxf_entities(doc)

            logger.info(
                "cad_dxf_success",
                file_path=file_path,
                layers=len(metadata.layers),
                blocks=len(metadata.blocks),
                texts=len(metadata.text_entities),
            )

            return metadata

        except ezdxf.DXFError as e:  # type: ignore[attr-defined]
            logger.error("cad_dxf_parse_failed", file_path=file_path, error=str(e))
            return CADMetadata(
                file_format="DXF",
                raw_metadata={"error": str(e)},
            )
        except Exception as e:
            logger.error("cad_dxf_failed", file_path=file_path, error=str(e), exc_info=True)
            return CADMetadata(
                file_format="DXF",
                raw_metadata={"error": str(e)},
            )

    def _extract_dxf_entities(self, doc: ezdxf.document.Drawing) -> CADMetadata:
        """Extract entities from ezdxf document.

        Args:
            doc: Loaded ezdxf Drawing document.

        Returns:
            CADMetadata with extracted entities.
        """
        metadata = CADMetadata(file_format="DXF")

        # Extract layers
        try:
            metadata.layers = [layer.dxf.name for layer in doc.layers]
        except Exception as e:
            logger.warning("cad_layers_extraction_failed", error=str(e))

        # Extract blocks
        try:
            metadata.blocks = [
                block.name
                for block in doc.blocks
                if not block.name.startswith("*")  # Skip anonymous blocks
            ]
        except Exception as e:
            logger.warning("cad_blocks_extraction_failed", error=str(e))

        # Extract text entities from modelspace
        try:
            msp = doc.modelspace()

            # TEXT entities
            for entity in msp.query("TEXT"):
                if hasattr(entity.dxf, "text"):
                    text_content = str(entity.dxf.text).strip()
                    if text_content:
                        metadata.text_entities.append(text_content)

            # MTEXT (multiline text) entities
            for entity in msp.query("MTEXT"):
                if hasattr(entity, "text"):
                    text_content = str(entity.text).strip()
                    if text_content:
                        metadata.text_entities.append(text_content)

        except Exception as e:
            logger.warning("cad_text_extraction_failed", error=str(e))

        # Extract dimension entities
        try:
            msp = doc.modelspace()
            for entity in msp.query("DIMENSION"):
                # Get dimension text if available
                if hasattr(entity.dxf, "text"):
                    dim_text = str(entity.dxf.text).strip()
                    if dim_text:
                        metadata.dimensions.append(dim_text)
                # Also store dimension type
                elif hasattr(entity, "dimtype"):
                    metadata.dimensions.append(f"<{entity.dimtype}>")

        except Exception as e:
            logger.warning("cad_dimensions_extraction_failed", error=str(e))

        # Store document metadata
        try:
            metadata.raw_metadata = {
                "dxf_version": doc.dxfversion,
                "encoding": doc.encoding,
                "layer_count": len(metadata.layers),
                "block_count": len(metadata.blocks),
            }
        except Exception as e:
            logger.warning("cad_raw_metadata_failed", error=str(e))

        return metadata

    def extract_step_metadata(self, file_path: str) -> CADMetadata:
        """Extract metadata from STEP file.

        STEP (ISO 10303) is a text-based 3D CAD format. Uses regex parsing
        to extract common entities:
        - PRODUCT: Product name and description
        - MATERIAL_DESIGNATION: Material specification
        - APPLICATION_PROTOCOL_DEFINITION: Protocol version (AP203, AP214, etc.)

        Args:
            file_path: Absolute path to STEP file.

        Returns:
            CADMetadata with extracted data, or empty result on failure.
        """
        path = Path(file_path)

        if not path.exists():
            logger.error("cad_file_not_found", file_path=file_path)
            return CADMetadata(
                file_format="STEP",
                raw_metadata={"error": "File not found"},
            )

        try:
            # Read file content (STEP is text-based)
            content = path.read_text(encoding="utf-8", errors="ignore")

            metadata = CADMetadata(file_format="STEP")

            # Extract PRODUCT entity: PRODUCT('id','name','description',...)
            product_pattern = r"PRODUCT\s*\(\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'"
            for match in re.finditer(product_pattern, content, re.IGNORECASE):
                _product_id, name, description = match.groups()
                if not metadata.product_name and name:
                    metadata.product_name = name.strip()
                if not metadata.description and description:
                    metadata.description = description.strip()

            # Extract MATERIAL_DESIGNATION
            material_pattern = r"MATERIAL_DESIGNATION\s*\([^,]*,\s*'([^']*)'"
            for match in re.finditer(material_pattern, content, re.IGNORECASE):
                material = match.group(1).strip()
                if material:
                    metadata.material = material
                    break  # Take first match

            # Extract APPLICATION_PROTOCOL_DEFINITION (e.g., AP203, AP214)
            protocol_pattern = r"APPLICATION_PROTOCOL_DEFINITION\s*\([^,]*,\s*'([^']*)'"
            for match in re.finditer(protocol_pattern, content, re.IGNORECASE):
                protocol = match.group(1).strip()
                if protocol:
                    metadata.protocol_version = protocol
                    break

            # Also check for schema name in header (e.g., "AP203_CONFIGURATION_CONTROLLED_3D_DESIGN")
            schema_pattern = r"FILE_SCHEMA\s*\(\s*\(\s*'([^']*)'"
            for match in re.finditer(schema_pattern, content, re.IGNORECASE):
                schema = match.group(1).strip()
                if "AP203" in schema.upper():
                    metadata.protocol_version = "AP203"
                elif "AP214" in schema.upper():
                    metadata.protocol_version = "AP214"
                break

            # Extract DIMENSIONAL_EXPONENTS (not typically useful for metadata, skip)

            # Store raw counts
            metadata.raw_metadata = {
                "file_size_bytes": path.stat().st_size,
                "product_entities": len(re.findall(r"PRODUCT\s*\(", content, re.IGNORECASE)),
                "material_entities": len(
                    re.findall(r"MATERIAL_DESIGNATION", content, re.IGNORECASE)
                ),
            }

            logger.info(
                "cad_step_success",
                file_path=file_path,
                product_name=metadata.product_name,
                material=metadata.material,
                protocol=metadata.protocol_version,
            )

            return metadata

        except Exception as e:
            logger.error("cad_step_failed", file_path=file_path, error=str(e), exc_info=True)
            return CADMetadata(
                file_format="STEP",
                raw_metadata={"error": str(e)},
            )

    def extract_metadata(self, file_path: str) -> CADMetadata:
        """Extract metadata from CAD file (auto-detects format).

        Args:
            file_path: Absolute path to CAD file.

        Returns:
            CADMetadata with extracted data.

        Raises:
            ValueError: If file extension is not supported.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in self._supported_dxf_types:
            return self.extract_dxf_metadata(file_path)
        elif suffix in self._supported_dwg_types:
            return self.extract_dwg_metadata(file_path)
        elif suffix in self._supported_step_types:
            return self.extract_step_metadata(file_path)
        else:
            logger.error("cad_unsupported_format", file_path=file_path, suffix=suffix)
            raise ValueError(
                f"Unsupported CAD format: {suffix}. "
                f"Supported: {self._supported_dxf_types | self._supported_dwg_types | self._supported_step_types}"
            )
