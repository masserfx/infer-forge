"""OCR text extraction module using Tesseract.

Extracts text from images (PNG, JPG, JPEG, TIFF, BMP) and PDF files.
Supports Czech and English languages with confidence scoring.
"""

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytesseract
import structlog
from PIL import Image

logger = structlog.get_logger(__name__)


@dataclass
class OCRResult:
    """Result of OCR text extraction.

    Attributes:
        text: Extracted text content.
        confidence: Average confidence score (0-100).
        language: Language codes used for OCR (e.g., 'ces+eng').
        page_count: Number of pages/images processed.
    """

    text: str
    confidence: float
    language: str
    page_count: int


class OCRProcessor:
    """Extracts text from images and PDFs using Tesseract OCR.

    Uses pytesseract wrapper for Tesseract OCR engine. Supports multiple
    image formats and PDFs. All operations are async-safe via thread executor.
    """

    def __init__(self, language: str = "ces+eng") -> None:
        """Initialize OCR processor.

        Args:
            language: Tesseract language codes ('+' separated for multiple).
                Default is 'ces+eng' for Czech and English.
        """
        self.language = language
        self._supported_image_types = {
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".tif",
            ".bmp",
        }
        self._supported_pdf_types = {".pdf"}

    async def extract_text(self, file_path: str) -> OCRResult:
        """Extract text from file on disk.

        Supports: PNG, JPG, JPEG, TIFF, BMP, PDF.

        Args:
            file_path: Absolute path to the file to process.

        Returns:
            OCRResult with extracted text and metadata.

        Raises:
            ValueError: If file type is not supported.
            FileNotFoundError: If file does not exist.
        """
        path = Path(file_path)

        if not path.exists():
            logger.error("ocr_file_not_found", file_path=file_path)
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix in self._supported_image_types:
            return await self._extract_from_image(file_path)
        elif suffix in self._supported_pdf_types:
            return await self._extract_from_pdf(file_path)
        else:
            logger.error("ocr_unsupported_type", file_path=file_path, suffix=suffix)
            raise ValueError(
                f"Unsupported file type: {suffix}. "
                f"Supported: {self._supported_image_types | self._supported_pdf_types}"
            )

    async def extract_text_from_bytes(self, data: bytes, content_type: str) -> OCRResult:
        """Extract text from raw bytes with known content type.

        Args:
            data: Raw file bytes.
            content_type: MIME type (e.g., 'image/png', 'application/pdf').

        Returns:
            OCRResult with extracted text and metadata.

        Raises:
            ValueError: If content type is not supported.
        """
        # Map content type to file extension
        content_type_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/tiff": ".tiff",
            "image/bmp": ".bmp",
            "application/pdf": ".pdf",
        }

        suffix = content_type_map.get(content_type.lower())
        if not suffix:
            logger.error("ocr_unsupported_content_type", content_type=content_type)
            raise ValueError(f"Unsupported content type: {content_type}")

        # Write to temporary file and process
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(data)
            tmp_path = tmp_file.name

        try:
            if suffix == ".pdf":
                result = await self._extract_from_pdf(tmp_path)
            else:
                result = await self._extract_from_image(tmp_path)
        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)

        return result

    async def _extract_from_image(self, file_path: str) -> OCRResult:
        """Extract text from a single image file.

        Args:
            file_path: Path to image file.

        Returns:
            OCRResult with extracted text and metadata.
        """
        loop = asyncio.get_running_loop()

        try:
            # Run OCR in thread executor (pytesseract is synchronous)
            text, confidence = await loop.run_in_executor(
                None, self._run_ocr_on_image, file_path
            )

            logger.info(
                "ocr_success",
                file_path=file_path,
                text_length=len(text),
                confidence=confidence,
            )

            return OCRResult(
                text=text,
                confidence=confidence,
                language=self.language,
                page_count=1,
            )

        except Exception as e:
            logger.error("ocr_failed", file_path=file_path, error=str(e), exc_info=True)
            # Return empty result on failure
            return OCRResult(
                text="",
                confidence=0.0,
                language=self.language,
                page_count=0,
            )

    def _run_ocr_on_image(self, file_path: str) -> tuple[str, float]:
        """Synchronous OCR execution on image.

        Args:
            file_path: Path to image file.

        Returns:
            Tuple of (extracted_text, average_confidence).
        """
        image = Image.open(file_path)

        # Extract text
        text = pytesseract.image_to_string(image, lang=self.language)

        # Get confidence scores
        try:
            data = pytesseract.image_to_data(image, lang=self.language, output_type="dict")
            # Filter out -1 confidence values (empty detections)
            confidences = [
                float(conf) for conf in data.get("conf", []) if int(conf) != -1
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        except Exception as e:
            logger.warning("ocr_confidence_failed", error=str(e))
            avg_confidence = 0.0

        return text.strip(), avg_confidence

    async def _extract_from_pdf(self, file_path: str) -> OCRResult:
        """Extract text from PDF file.

        First attempts to use pdf2image if available, otherwise falls back
        to direct PyMuPDF processing.

        Args:
            file_path: Path to PDF file.

        Returns:
            OCRResult with extracted text and metadata.
        """
        try:
            # Try pdf2image approach (better quality for OCR)
            return await self._extract_from_pdf_with_pdf2image(file_path)
        except ImportError:
            logger.warning("pdf2image_not_available", fallback="pymupdf")
            # Fall back to PyMuPDF direct rendering
            return await self._extract_from_pdf_with_pymupdf(file_path)

    async def _extract_from_pdf_with_pdf2image(self, file_path: str) -> OCRResult:
        """Extract text from PDF using pdf2image for conversion.

        Args:
            file_path: Path to PDF file.

        Returns:
            OCRResult with extracted text and metadata.

        Raises:
            ImportError: If pdf2image is not installed.
        """
        from pdf2image import convert_from_path

        loop = asyncio.get_running_loop()

        try:
            # Convert PDF pages to images
            images = await loop.run_in_executor(None, convert_from_path, file_path)

            all_text = []
            all_confidences = []

            # Process each page
            for _page_num, image in enumerate(images, start=1):
                # Save to temporary file for pytesseract
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    image.save(tmp_path, "PNG")

                try:
                    text, confidence = await loop.run_in_executor(
                        None, self._run_ocr_on_image, tmp_path
                    )
                    all_text.append(text)
                    all_confidences.append(confidence)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            combined_text = "\n\n".join(all_text)
            avg_confidence = (
                sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            )

            logger.info(
                "ocr_pdf_success",
                file_path=file_path,
                pages=len(images),
                text_length=len(combined_text),
                confidence=avg_confidence,
            )

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                language=self.language,
                page_count=len(images),
            )

        except Exception as e:
            logger.error(
                "ocr_pdf_failed", file_path=file_path, error=str(e), exc_info=True
            )
            return OCRResult(
                text="",
                confidence=0.0,
                language=self.language,
                page_count=0,
            )

    async def _extract_from_pdf_with_pymupdf(self, file_path: str) -> OCRResult:
        """Extract text from PDF using PyMuPDF (fitz) for rendering.

        Args:
            file_path: Path to PDF file.

        Returns:
            OCRResult with extracted text and metadata.
        """
        import fitz  # PyMuPDF

        loop = asyncio.get_running_loop()

        try:
            # Open PDF
            pdf_doc = fitz.open(file_path)

            all_text = []
            all_confidences = []

            # Process each page
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]

                # Render page to image (150 DPI for good OCR quality)
                pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72))

                # Convert to PIL Image
                img_data = pix.tobytes("png")

                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    tmp_file.write(img_data)

                try:
                    text, confidence = await loop.run_in_executor(
                        None, self._run_ocr_on_image, tmp_path
                    )
                    all_text.append(text)
                    all_confidences.append(confidence)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            pdf_doc.close()

            combined_text = "\n\n".join(all_text)
            avg_confidence = (
                sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            )

            logger.info(
                "ocr_pdf_success",
                file_path=file_path,
                pages=len(pdf_doc),
                text_length=len(combined_text),
                confidence=avg_confidence,
            )

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                language=self.language,
                page_count=len(pdf_doc),
            )

        except Exception as e:
            logger.error(
                "ocr_pdf_failed", file_path=file_path, error=str(e), exc_info=True
            )
            return OCRResult(
                text="",
                confidence=0.0,
                language=self.language,
                page_count=0,
            )
