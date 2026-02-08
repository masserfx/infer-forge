"""Tests for CAD metadata extraction (DXF, DWG, STEP)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.integrations.ocr.cad_metadata import CADMetadata, CADMetadataExtractor
from app.integrations.ocr.processor import OCRProcessor


class TestCADMetadataExtractor:
    """Tests for CADMetadataExtractor class."""

    @pytest.fixture
    def extractor(self) -> CADMetadataExtractor:
        """Create CAD metadata extractor."""
        return CADMetadataExtractor()

    def test_extract_dxf_metadata(self, extractor: CADMetadataExtractor) -> None:
        """Test extraction from DXF file."""
        # Mock ezdxf readfile
        mock_doc = MagicMock()

        # Mock layers
        mock_layer1 = MagicMock()
        mock_layer1.dxf.name = "0"
        mock_layer2 = MagicMock()
        mock_layer2.dxf.name = "Dimensions"
        mock_doc.layers = [mock_layer1, mock_layer2]

        # Mock blocks
        mock_block1 = MagicMock()
        mock_block1.name = "PartA"
        mock_block2 = MagicMock()
        mock_block2.name = "*ModelSpace"  # Should be skipped
        mock_doc.blocks = [mock_block1, mock_block2]

        # Mock modelspace with text entities
        mock_text = MagicMock()
        mock_text.dxf.text = "Material: S235JR"

        mock_mtext = MagicMock()
        mock_mtext.text = "DN 100 PN 16"

        mock_msp = MagicMock()
        mock_msp.query.side_effect = lambda entity_type: {
            "TEXT": [mock_text],
            "MTEXT": [mock_mtext],
            "DIMENSION": [],
        }.get(entity_type, [])

        mock_doc.modelspace.return_value = mock_msp
        mock_doc.dxfversion = "AC1027"
        mock_doc.encoding = "utf-8"

        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"dummy dxf content")

        try:
            with patch(
                "app.integrations.ocr.cad_metadata.ezdxf.readfile", return_value=mock_doc
            ) as mock_readfile:
                metadata = extractor.extract_dxf_metadata(tmp_path)

                # Verify readfile was called
                mock_readfile.assert_called_once_with(tmp_path)

                # Verify extracted data
                assert metadata.file_format == "DXF"
                assert metadata.layers == ["0", "Dimensions"]
                assert metadata.blocks == ["PartA"]  # *ModelSpace should be filtered
                assert "Material: S235JR" in metadata.text_entities
                assert "DN 100 PN 16" in metadata.text_entities
                assert metadata.raw_metadata["dxf_version"] == "AC1027"
                assert metadata.raw_metadata["layer_count"] == 2

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_extract_dxf_with_dimensions(self, extractor: CADMetadataExtractor) -> None:
        """Test extraction of dimension entities from DXF."""
        mock_doc = MagicMock()
        mock_doc.layers = []
        mock_doc.blocks = []

        # Mock dimension entity
        mock_dim = MagicMock()
        mock_dim.dxf.text = "150.00"

        mock_msp = MagicMock()
        mock_msp.query.side_effect = lambda entity_type: {
            "TEXT": [],
            "MTEXT": [],
            "DIMENSION": [mock_dim],
        }.get(entity_type, [])

        mock_doc.modelspace.return_value = mock_msp
        mock_doc.dxfversion = "AC1027"
        mock_doc.encoding = "utf-8"

        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"dummy dxf content")

        try:
            with patch("app.integrations.ocr.cad_metadata.ezdxf.readfile", return_value=mock_doc):
                metadata = extractor.extract_dxf_metadata(tmp_path)

                assert "150.00" in metadata.dimensions

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_extract_dwg_unsupported(self, extractor: CADMetadataExtractor) -> None:
        """Test that binary DWG returns empty result with error note."""
        with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"Binary DWG content (not readable by ezdxf)")

        try:
            # Mock ezdxf to raise DXFError
            with patch(
                "app.integrations.ocr.cad_metadata.ezdxf.readfile",
                side_effect=Exception("DXF Error: Invalid format"),
            ):
                metadata = extractor.extract_dwg_metadata(tmp_path)

                assert metadata.file_format == "DWG"
                assert metadata.layers == []
                assert metadata.blocks == []
                assert "error" in metadata.raw_metadata

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_extract_step_metadata(self, extractor: CADMetadataExtractor) -> None:
        """Test extraction from STEP file."""
        # Sample STEP content
        step_content = """ISO-10303-21;
HEADER;
FILE_SCHEMA(('AP203_CONFIGURATION_CONTROLLED_3D_DESIGN_OF_MECHANICAL_PARTS_AND_ASSEMBLIES_MIM_LF'));
ENDSEC;
DATA;
#10=PRODUCT('12345','Flange DN100 PN16','Flange connector for piping',#20);
#20=PRODUCT_DEFINITION_CONTEXT('manufacturing',#21,'production');
#30=MATERIAL_DESIGNATION(#40,'S235JR');
#50=APPLICATION_PROTOCOL_DEFINITION('international standard','ap203_configuration_controlled_3d_design',2011,#60);
ENDSEC;
END-ISO-10303-21;
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".step", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(step_content)

        try:
            metadata = extractor.extract_step_metadata(tmp_path)

            assert metadata.file_format == "STEP"
            assert metadata.product_name == "Flange DN100 PN16"
            assert metadata.description == "Flange connector for piping"
            assert metadata.material == "S235JR"
            assert metadata.protocol_version == "AP203"  # From FILE_SCHEMA
            assert metadata.raw_metadata["product_entities"] == 1

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_extract_step_product_name(self, extractor: CADMetadataExtractor) -> None:
        """Test parsing of PRODUCT name from STEP."""
        step_content = """DATA;
#1=PRODUCT('PART-001','Valve Body','Main valve body assembly',#2);
ENDSEC;
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".stp", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(step_content)

        try:
            metadata = extractor.extract_step_metadata(tmp_path)

            assert metadata.product_name == "Valve Body"
            assert metadata.description == "Main valve body assembly"

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_extract_step_material(self, extractor: CADMetadataExtractor) -> None:
        """Test parsing of material designation from STEP."""
        step_content = """DATA;
#10=MATERIAL_DESIGNATION(#11,'316L Stainless Steel');
ENDSEC;
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".step", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(step_content)

        try:
            metadata = extractor.extract_step_metadata(tmp_path)

            assert metadata.material == "316L Stainless Steel"

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_unsupported_format(self, extractor: CADMetadataExtractor) -> None:
        """Test that unsupported format raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"dummy content")

        try:
            with pytest.raises(ValueError, match="Unsupported CAD format"):
                extractor.extract_metadata(tmp_path)

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_file_not_found(self, extractor: CADMetadataExtractor) -> None:
        """Test handling of non-existent file."""
        metadata = extractor.extract_dxf_metadata("/nonexistent/file.dxf")

        assert metadata.file_format == "DXF"
        assert metadata.raw_metadata.get("error") == "File not found"


class TestOCRProcessorCAD:
    """Tests for OCRProcessor CAD integration."""

    @pytest.fixture
    def processor(self) -> OCRProcessor:
        """Create OCR processor."""
        return OCRProcessor()

    @pytest.mark.asyncio
    async def test_extract_cad_metadata_dxf(self, processor: OCRProcessor) -> None:
        """Test extract_cad_metadata with DXF file."""
        mock_metadata = CADMetadata(
            file_format="DXF",
            layers=["0", "Dimensions"],
            blocks=["PartA"],
            text_entities=["Material: S235JR"],
            dimensions=["100.0"],
        )

        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"dummy dxf content")

        try:
            with patch.object(
                processor._cad_extractor, "extract_metadata", return_value=mock_metadata
            ):
                metadata = await processor.extract_cad_metadata(tmp_path)

                assert metadata.file_format == "DXF"
                assert metadata.layers == ["0", "Dimensions"]
                assert metadata.blocks == ["PartA"]

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_extract_cad_metadata_step(self, processor: OCRProcessor) -> None:
        """Test extract_cad_metadata with STEP file."""
        mock_metadata = CADMetadata(
            file_format="STEP",
            product_name="Flange DN100",
            material="S235JR",
            protocol_version="AP203",
        )

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"dummy step content")

        try:
            with patch.object(
                processor._cad_extractor, "extract_metadata", return_value=mock_metadata
            ):
                metadata = await processor.extract_cad_metadata(tmp_path)

                assert metadata.file_format == "STEP"
                assert metadata.product_name == "Flange DN100"
                assert metadata.material == "S235JR"

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_extract_cad_metadata_unsupported(self, processor: OCRProcessor) -> None:
        """Test extract_cad_metadata with unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"text content")

        try:
            with pytest.raises(ValueError, match="Unsupported CAD file type"):
                await processor.extract_cad_metadata(tmp_path)

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_extract_cad_metadata_file_not_found(self, processor: OCRProcessor) -> None:
        """Test extract_cad_metadata with non-existent file."""
        with pytest.raises(FileNotFoundError):
            await processor.extract_cad_metadata("/nonexistent/file.dxf")

    @pytest.mark.asyncio
    async def test_extract_cad_metadata_from_bytes(self, processor: OCRProcessor) -> None:
        """Test extract_cad_metadata_from_bytes."""
        mock_metadata = CADMetadata(
            file_format="DXF",
            layers=["0"],
            blocks=["PartA"],
        )

        dxf_bytes = b"dummy dxf content"

        with patch.object(
            processor._cad_extractor, "extract_metadata", return_value=mock_metadata
        ):
            metadata = await processor.extract_cad_metadata_from_bytes(
                dxf_bytes, "application/dxf"
            )

            assert metadata.file_format == "DXF"
            assert metadata.layers == ["0"]

    @pytest.mark.asyncio
    async def test_extract_cad_metadata_from_bytes_unsupported(
        self, processor: OCRProcessor
    ) -> None:
        """Test extract_cad_metadata_from_bytes with unsupported content type."""
        with pytest.raises(ValueError, match="Unsupported CAD content type"):
            await processor.extract_cad_metadata_from_bytes(b"data", "application/json")

    @pytest.mark.asyncio
    async def test_extract_cad_metadata_handles_exception(
        self, processor: OCRProcessor
    ) -> None:
        """Test that extract_cad_metadata returns empty metadata on exception."""
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"dummy dxf content")

        try:
            with patch.object(
                processor._cad_extractor,
                "extract_metadata",
                side_effect=Exception("Extraction failed"),
            ):
                metadata = await processor.extract_cad_metadata(tmp_path)

                # Should return empty metadata with error
                assert metadata.file_format == "DXF"
                assert "error" in metadata.raw_metadata

        finally:
            Path(tmp_path).unlink(missing_ok=True)
