"""Unit tests for OCR processor (mocked Tesseract)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.integrations.ocr.processor import OCRProcessor, OCRResult


class TestOCRResult:
    """Tests for OCRResult dataclass."""

    def test_valid_result(self) -> None:
        """Test creating a valid OCR result."""
        result = OCRResult(
            text="Extracted text content",
            confidence=85.5,
            language="ces+eng",
            page_count=1,
        )

        assert result.text == "Extracted text content"
        assert result.confidence == 85.5
        assert result.language == "ces+eng"
        assert result.page_count == 1

    def test_empty_result(self) -> None:
        """Test creating an empty OCR result."""
        result = OCRResult(
            text="",
            confidence=0.0,
            language="ces+eng",
            page_count=0,
        )

        assert result.text == ""
        assert result.confidence == 0.0
        assert result.page_count == 0

    def test_multipage_result(self) -> None:
        """Test creating a multi-page OCR result."""
        result = OCRResult(
            text="Page 1\n\nPage 2\n\nPage 3",
            confidence=92.3,
            language="ces",
            page_count=3,
        )

        assert result.page_count == 3
        assert "\n\n" in result.text


class TestOCRProcessor:
    """Tests for OCRProcessor class."""

    @pytest.fixture
    def processor(self) -> OCRProcessor:
        """Create OCR processor with default language."""
        return OCRProcessor(language="ces+eng")

    @pytest.fixture
    def temp_image_path(self, tmp_path: Path) -> str:
        """Create a temporary test image file."""
        image_path = tmp_path / "test_image.png"

        # Create a simple test image with PIL
        img = Image.new("RGB", (200, 100), color="white")
        img.save(str(image_path), "PNG")

        return str(image_path)

    @pytest.fixture
    def temp_unsupported_file(self, tmp_path: Path) -> str:
        """Create an unsupported file type."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("This is a text file")
        return str(file_path)

    @pytest.mark.asyncio
    async def test_processor_initialization(self) -> None:
        """Test OCR processor initialization with custom language."""
        processor = OCRProcessor(language="eng")
        assert processor.language == "eng"

        processor_czech = OCRProcessor(language="ces")
        assert processor_czech.language == "ces"

        processor_default = OCRProcessor()
        assert processor_default.language == "ces+eng"

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_from_image(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        temp_image_path: str,
    ) -> None:
        """Test extracting text from image file."""
        # Mock Tesseract responses - confidence values as strings (as pytesseract returns them)
        mock_image_to_string.return_value = "Faktura č. 2024001\nCelkem: 15 000 Kč"
        mock_image_to_data.return_value = {
            "conf": [95.5, 92.3, 88.1, 90.0, -1]  # Note: -1 should be filtered
        }

        result = await processor.extract_text(temp_image_path)

        assert isinstance(result, OCRResult)
        assert result.text == "Faktura č. 2024001\nCelkem: 15 000 Kč"
        assert result.confidence > 0
        assert result.language == "ces+eng"
        assert result.page_count == 1

        # Verify Tesseract was called
        mock_image_to_string.assert_called_once()
        mock_image_to_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_text_from_nonexistent_file(
        self,
        processor: OCRProcessor,
    ) -> None:
        """Test extracting text from non-existent file raises error."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            await processor.extract_text("/nonexistent/path/image.png")

    @pytest.mark.asyncio
    async def test_extract_text_from_unsupported_format(
        self,
        processor: OCRProcessor,
        temp_unsupported_file: str,
    ) -> None:
        """Test extracting text from unsupported file type raises error."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            await processor.extract_text(temp_unsupported_file)

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_handles_ocr_failure(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        temp_image_path: str,
    ) -> None:
        """Test OCR gracefully handles extraction failures."""
        # Mock Tesseract to raise exception
        mock_image_to_string.side_effect = Exception("Tesseract error")

        result = await processor.extract_text(temp_image_path)

        # Should return empty result instead of raising
        assert result.text == ""
        assert result.confidence == 0.0
        assert result.page_count == 0

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_calculates_average_confidence(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        temp_image_path: str,
    ) -> None:
        """Test confidence score is calculated correctly."""
        mock_image_to_string.return_value = "Test text"
        # Confidence values: 90, 85, 95, -1 (invalid)
        # Average should be (90 + 85 + 95) / 3 = 90.0
        mock_image_to_data.return_value = {
            "conf": ["90", "85", "95", "-1"]
        }

        result = await processor.extract_text(temp_image_path)

        assert result.confidence == 90.0

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_from_bytes_png(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        temp_image_path: str,
    ) -> None:
        """Test extracting text from PNG image bytes."""
        # Read test image as bytes
        with open(temp_image_path, "rb") as f:
            image_bytes = f.read()

        mock_image_to_string.return_value = "Text from bytes"
        mock_image_to_data.return_value = {"conf": [92.5]}

        result = await processor.extract_text_from_bytes(
            data=image_bytes,
            content_type="image/png",
        )

        assert result.text == "Text from bytes"
        assert result.confidence > 0
        assert result.page_count == 1

    @pytest.mark.asyncio
    async def test_extract_text_from_bytes_unsupported_type(
        self,
        processor: OCRProcessor,
    ) -> None:
        """Test extracting text from unsupported content type raises error."""
        with pytest.raises(ValueError, match="Unsupported content type"):
            await processor.extract_text_from_bytes(
                data=b"test data",
                content_type="application/xml",
            )

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_from_bytes_jpeg(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        tmp_path: Path,
    ) -> None:
        """Test extracting text from JPEG image bytes."""
        # Create JPEG test image
        jpeg_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(str(jpeg_path), "JPEG")

        with open(jpeg_path, "rb") as f:
            jpeg_bytes = f.read()

        mock_image_to_string.return_value = "JPEG content"
        mock_image_to_data.return_value = {"conf": ["88.0"]}

        result = await processor.extract_text_from_bytes(
            data=jpeg_bytes,
            content_type="image/jpeg",
        )

        assert result.text == "JPEG content"
        assert result.page_count == 1

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_strips_whitespace(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        temp_image_path: str,
    ) -> None:
        """Test extracted text is stripped of leading/trailing whitespace."""
        mock_image_to_string.return_value = "   \n  Text with spaces  \n\n  "
        mock_image_to_data.return_value = {"conf": ["90"]}

        result = await processor.extract_text(temp_image_path)

        assert result.text == "Text with spaces"

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_confidence_fallback(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        temp_image_path: str,
    ) -> None:
        """Test confidence defaults to 0 when data extraction fails."""
        mock_image_to_string.return_value = "Valid text"
        # Mock confidence extraction failure
        mock_image_to_data.side_effect = Exception("Data extraction failed")

        result = await processor.extract_text(temp_image_path)

        assert result.text == "Valid text"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_empty_confidence_list(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        temp_image_path: str,
    ) -> None:
        """Test confidence defaults to 0 when all values are filtered out."""
        mock_image_to_string.return_value = "Some text"
        # All confidence values are -1 (invalid)
        mock_image_to_data.return_value = {"conf": ["-1", "-1", "-1"]}

        result = await processor.extract_text(temp_image_path)

        assert result.confidence == 0.0

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_supported_image_formats(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        processor: OCRProcessor,
        tmp_path: Path,
    ) -> None:
        """Test all supported image formats are recognized."""
        supported_formats = [
            ("test.png", "PNG"),
            ("test.jpg", "JPEG"),
            ("test.jpeg", "JPEG"),
            ("test.tiff", "TIFF"),
            ("test.bmp", "BMP"),
        ]

        mock_image_to_string.return_value = "Test"
        mock_image_to_data.return_value = {"conf": ["90"]}

        for filename, format_type in supported_formats:
            file_path = tmp_path / filename
            img = Image.new("RGB", (50, 50), color="white")
            img.save(str(file_path), format_type)

            result = await processor.extract_text(str(file_path))
            assert result.text == "Test"
            assert result.page_count == 1

    @pytest.mark.asyncio
    @patch("app.integrations.ocr.processor.pytesseract.image_to_string")
    @patch("app.integrations.ocr.processor.pytesseract.image_to_data")
    async def test_extract_text_uses_correct_language(
        self,
        mock_image_to_data: MagicMock,
        mock_image_to_string: MagicMock,
        temp_image_path: str,
    ) -> None:
        """Test OCR uses the configured language parameter."""
        processor_eng = OCRProcessor(language="eng")

        mock_image_to_string.return_value = "English text"
        mock_image_to_data.return_value = {"conf": ["95"]}

        result = await processor_eng.extract_text(temp_image_path)

        # Verify language was passed to pytesseract
        call_args = mock_image_to_string.call_args
        assert call_args[1]["lang"] == "eng"
        assert result.language == "eng"
