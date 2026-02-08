r"""Document Type Detector - 3-level detection: filename, content-type, OCR text.

Detects DocumentCategory for email attachments without AI:
- L1: Filename patterns (.dwg → vykres, faktura* → faktura, etc.)
- L2: MIME type (application/acad → vykres)
- L3: OCR text regex (DN\d+.*PN\d+ → vykres, IČO.*splatnost → faktura)
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# L1: Filename pattern mappings (case-insensitive)
_FILENAME_PATTERNS = {
    "vykres": [r"\.dwg$", r"\.dxf$", r"vykres", r"drawing"],
    "faktura": [r"faktura", r"invoice", r"^FV", r"^FA"],
    "atestace": [r"atest", r"certificate", r"certifikat"],
    "nabidka": [r"nabidka", r"nabídka", r"offer", r"quotation"],
    "objednavka": [r"objednavka", r"objednávka", r"^PO\d+", r"purchase"],
    "wps": [r"wps", r"wpqr", r"svaren", r"weld"],
    "protokol": [r"protokol", r"protocol", r"zkouska", r"test"],
}

# L2: MIME type mappings
_MIME_TYPE_MAP = {
    "application/acad": "vykres",
    "application/x-acad": "vykres",
    "application/x-autocad": "vykres",
    "application/dxf": "vykres",
    "image/vnd.dwg": "vykres",
    "image/x-dwg": "vykres",
}

# L3: OCR text patterns
_OCR_PATTERNS = {
    "vykres": [
        re.compile(r"DN\s*\d+.*PN\s*\d+", re.IGNORECASE | re.DOTALL),
        re.compile(r"ISO\s*\d+", re.IGNORECASE),
        re.compile(r"rozměry\s*:\s*\d+", re.IGNORECASE),
    ],
    "faktura": [
        re.compile(r"IČ[OD]?\s*:?\s*\d+.*splat", re.IGNORECASE | re.DOTALL),
        re.compile(r"daňový\s+doklad", re.IGNORECASE),
        re.compile(r"faktura.*číslo", re.IGNORECASE),
    ],
    "atestace": [
        re.compile(r"EN\s*10204", re.IGNORECASE),
        re.compile(r"certifikát.*materiál", re.IGNORECASE),
        re.compile(r"tavba\s*č", re.IGNORECASE),
    ],
    "wps": [
        re.compile(r"\bWPS\b", re.IGNORECASE),
        re.compile(r"\bWPQR\b", re.IGNORECASE),
        re.compile(r"svařování.*postup", re.IGNORECASE),
    ],
    "protokol": [
        re.compile(r"protokol.*zkoušk", re.IGNORECASE),
        re.compile(r"NDT.*report", re.IGNORECASE),
        re.compile(r"výsledky\s+měření", re.IGNORECASE),
    ],
}


class DocumentTypeDetector:
    """Detects document category using 3-level heuristics.

    Confidence levels:
    - L1 (filename): 0.90
    - L2 (MIME): 0.85
    - L3 (OCR text): 0.75
    - Default (ostatni): 0.50
    """

    def detect(
        self, filename: str, content_type: str, ocr_text: str | None = None
    ) -> tuple[str, float]:
        """Detect document category.

        Args:
            filename: Original filename
            content_type: MIME type
            ocr_text: OCR extracted text (optional)

        Returns:
            (category, confidence) tuple where category is DocumentCategory value
        """
        # L1: Filename patterns
        filename_category = self._detect_from_filename(filename)
        if filename_category:
            logger.info(
                "document_type_detected_filename",
                category=filename_category,
                confidence=0.90,
                filename=filename,
            )
            return filename_category, 0.90

        # L2: MIME type
        mime_category = _MIME_TYPE_MAP.get(content_type.lower())
        if mime_category:
            logger.info(
                "document_type_detected_mime",
                category=mime_category,
                confidence=0.85,
                content_type=content_type,
            )
            return mime_category, 0.85

        # L3: OCR text patterns
        if ocr_text:
            ocr_category = self._detect_from_ocr(ocr_text)
            if ocr_category:
                logger.info(
                    "document_type_detected_ocr",
                    category=ocr_category,
                    confidence=0.75,
                    ocr_preview=ocr_text[:100],
                )
                return ocr_category, 0.75

        # Default fallback
        logger.debug(
            "document_type_default",
            category="ostatni",
            confidence=0.50,
            filename=filename,
            content_type=content_type,
        )
        return "ostatni", 0.50

    def _detect_from_filename(self, filename: str) -> str | None:
        """Detect category from filename patterns.

        Args:
            filename: Original filename

        Returns:
            Category string or None
        """
        filename_lower = filename.lower()
        for category, patterns in _FILENAME_PATTERNS.items():
            for pattern_str in patterns:
                if re.search(pattern_str, filename_lower):
                    return category
        return None

    def _detect_from_ocr(self, ocr_text: str) -> str | None:
        """Detect category from OCR text patterns.

        Args:
            ocr_text: OCR extracted text

        Returns:
            Category string or None
        """
        for category, patterns in _OCR_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(ocr_text):
                    return category
        return None
