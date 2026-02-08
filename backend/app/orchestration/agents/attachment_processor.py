"""Attachment Processor - OCR + document type detection for email attachments.

Orchestrates:
- OCR text extraction (images, PDFs)
- CAD metadata extraction (DWG, DXF, STEP)
- Document category detection
- Document record creation/update
- EmailAttachment record updates
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.integrations.ocr.processor import OCRProcessor
from app.models.document import Document, DocumentCategory
from app.models.email_attachment import EmailAttachment, OCRStatus
from app.orchestration.agents.document_type_detector import DocumentTypeDetector

logger = structlog.get_logger(__name__)


class AttachmentProcessor:
    """Processes email attachments: OCR, type detection, document creation.

    Responsibilities:
    - Run OCR on images/PDFs
    - Extract CAD metadata
    - Detect document category
    - Create Document records
    - Update EmailAttachment status
    """

    def __init__(self) -> None:
        self.ocr_processor = OCRProcessor(language="ces+eng")
        self.type_detector = DocumentTypeDetector()

    async def process(
        self, attachment_id: UUID, file_path: str, content_type: str, filename: str
    ) -> dict:
        """Process single attachment: OCR + type detection.

        Args:
            attachment_id: EmailAttachment UUID
            file_path: Absolute path to attachment file
            content_type: MIME type
            filename: Original filename

        Returns:
            dict with document_id, ocr_text_length, ocr_confidence, detected_category
        """
        logger.info(
            "attachment_processing_start",
            attachment_id=str(attachment_id),
            filename=filename,
            content_type=content_type,
        )

        async with AsyncSessionLocal() as session:
            # Load attachment record
            result = await session.execute(
                select(EmailAttachment).where(EmailAttachment.id == attachment_id)
            )
            attachment = result.scalar_one_or_none()
            if not attachment:
                logger.error("attachment_not_found", attachment_id=str(attachment_id))
                raise ValueError(f"Attachment not found: {attachment_id}")

            # Update status to RUNNING
            attachment.ocr_status = OCRStatus.RUNNING
            await session.commit()

        # Run OCR/metadata extraction (outside session for long operations)
        ocr_text: str | None = None
        ocr_confidence: float | None = None
        processing_error: str | None = None

        try:
            # Check file type
            path = Path(file_path)
            suffix = path.suffix.lower()

            # Process based on file type
            if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".pdf"}:
                # Image or PDF → OCR
                ocr_result = await self.ocr_processor.extract_text(file_path)
                ocr_text = ocr_result.text
                ocr_confidence = ocr_result.confidence / 100.0  # Normalize to 0-1
                logger.info(
                    "ocr_complete",
                    attachment_id=str(attachment_id),
                    text_length=len(ocr_text),
                    confidence=ocr_confidence,
                )
            elif suffix in {".dxf", ".dwg", ".stp", ".step"}:
                # CAD file → metadata extraction
                cad_metadata = await self.ocr_processor.extract_cad_metadata(file_path)
                ocr_text = self._format_cad_metadata(cad_metadata)
                ocr_confidence = 0.95  # High confidence for structured metadata
                logger.info(
                    "cad_metadata_extracted",
                    attachment_id=str(attachment_id),
                    metadata_keys=len(cad_metadata.raw_metadata),
                )
            else:
                # Unsupported type → skip
                logger.info("ocr_skipped_unsupported_type", suffix=suffix)
                ocr_text = None
                ocr_confidence = None

        except Exception as e:
            logger.exception("attachment_processing_error", attachment_id=str(attachment_id))
            processing_error = str(e)

        # Detect document category (always run, even without OCR)
        detected_category, detection_confidence = self.type_detector.detect(
            filename, content_type, ocr_text
        )

        # Update database (session-bound operations)
        async with AsyncSessionLocal() as session:
            # Reload attachment
            result = await session.execute(
                select(EmailAttachment).where(EmailAttachment.id == attachment_id)
            )
            attachment = result.scalar_one()

            # Update attachment record
            if processing_error:
                attachment.ocr_status = OCRStatus.FAILED
                attachment.processing_error = processing_error
                await session.commit()
                logger.error(
                    "attachment_processing_failed",
                    attachment_id=str(attachment_id),
                    error=processing_error,
                )
                return {
                    "document_id": None,
                    "ocr_text_length": 0,
                    "ocr_confidence": 0.0,
                    "detected_category": detected_category,
                    "error": processing_error,
                }
            else:
                attachment.ocr_status = (
                    OCRStatus.COMPLETE if ocr_text else OCRStatus.SKIPPED
                )
                attachment.ocr_confidence = ocr_confidence
                attachment.detected_category = detected_category

            # Create or update Document record
            if attachment.document_id:
                # Update existing document
                doc_result = await session.execute(
                    select(Document).where(Document.id == attachment.document_id)
                )
                document = doc_result.scalar_one_or_none()
                if document:
                    document.ocr_text = ocr_text
                    document.category = DocumentCategory(detected_category)
                    document_id = document.id
                else:
                    # Document was deleted, create new one
                    document = self._create_document(
                        attachment, filename, content_type, ocr_text, detected_category
                    )
                    session.add(document)
                    await session.flush()
                    document_id = document.id
                    attachment.document_id = document_id
            else:
                # Create new document
                document = self._create_document(
                    attachment, filename, content_type, ocr_text, detected_category
                )
                session.add(document)
                await session.flush()
                document_id = document.id
                attachment.document_id = document_id

            await session.commit()

        logger.info(
            "attachment_processing_complete",
            attachment_id=str(attachment_id),
            document_id=str(document_id),
            ocr_text_length=len(ocr_text) if ocr_text else 0,
            detected_category=detected_category,
        )

        return {
            "document_id": document_id,
            "ocr_text_length": len(ocr_text) if ocr_text else 0,
            "ocr_confidence": ocr_confidence or 0.0,
            "detected_category": detected_category,
        }

    def _create_document(
        self,
        attachment: EmailAttachment,
        filename: str,
        content_type: str,
        ocr_text: str | None,
        detected_category: str,
    ) -> Document:
        """Create Document record from attachment.

        Args:
            attachment: EmailAttachment record
            filename: Original filename
            content_type: MIME type
            ocr_text: Extracted text
            detected_category: Detected category string

        Returns:
            Document instance (not yet persisted)
        """
        return Document(
            entity_type="inbox_message",
            entity_id=attachment.inbox_message_id,
            file_name=filename,
            file_path=attachment.file_path,
            mime_type=content_type,
            file_size=attachment.file_size,
            category=DocumentCategory(detected_category),
            ocr_text=ocr_text,
            version=1,
        )

    @staticmethod
    def _format_cad_metadata(cad_metadata) -> str:  # type: ignore
        """Format CAD metadata as text for storage.

        Args:
            cad_metadata: CADMetadata object

        Returns:
            Formatted text string
        """
        lines = [f"CAD Format: {cad_metadata.file_format}"]
        if cad_metadata.layers:
            lines.append(f"Layers ({len(cad_metadata.layers)}): {', '.join(cad_metadata.layers[:10])}")
        if cad_metadata.blocks:
            lines.append(f"Blocks ({len(cad_metadata.blocks)}): {', '.join(cad_metadata.blocks[:10])}")
        if cad_metadata.text_entities:
            lines.append(f"Text entities: {len(cad_metadata.text_entities)}")
        if cad_metadata.dimensions:
            lines.append(f"Dimensions: {len(cad_metadata.dimensions)}")
        if cad_metadata.product_name:
            lines.append(f"Product: {cad_metadata.product_name}")
        if cad_metadata.material:
            lines.append(f"Material: {cad_metadata.material}")
        return "\n".join(lines)
