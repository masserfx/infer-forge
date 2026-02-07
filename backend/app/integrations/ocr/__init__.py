"""OCR (Optical Character Recognition) integration module.

Provides text extraction from images and PDF documents using Tesseract OCR.
Supports Czech and English languages with confidence scoring.
"""

from app.integrations.ocr.processor import OCRProcessor, OCRResult

__all__ = ["OCRProcessor", "OCRResult"]
