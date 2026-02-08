"""Email Ingestion Agent - stores raw email and attachments to DB + filesystem.

Pure I/O operations (no AI):
- Creates InboxMessage record
- Saves attachments to disk: {UPLOAD_DIR}/attachments/{inbox_message_id}/{filename}
- Creates EmailAttachment records
- Extracts thread_id from email headers
"""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.integrations.email.imap_client import RawEmail
from app.models.email_attachment import EmailAttachment, OCRStatus
from app.models.inbox import InboxMessage, InboxStatus

logger = structlog.get_logger(__name__)
settings = get_settings()


class EmailIngestionAgent:
    """Ingests raw email data into database and filesystem.

    Responsibilities:
    - Create InboxMessage from RawEmail
    - Save attachments to disk
    - Create EmailAttachment records
    - Extract thread_id from References/In-Reply-To headers
    """

    _THREAD_ID_PATTERN = re.compile(r"<([^>]+)>")

    async def process(
        self,
        raw_email: RawEmail,
        references_header: str | None = None,
        in_reply_to_header: str | None = None,
    ) -> dict:
        """Process raw email and persist to DB + filesystem.

        Args:
            raw_email: Parsed email from IMAP
            references_header: Raw References header (space-separated message IDs)
            in_reply_to_header: Raw In-Reply-To header (single message ID)

        Returns:
            dict with inbox_message_id, attachment_ids, from_email, subject, body_text, thread_id
        """
        logger.info(
            "email_ingestion_start",
            message_id=raw_email.message_id,
            from_email=raw_email.from_email,
            subject=raw_email.subject,
            attachment_count=len(raw_email.attachments),
        )

        async with AsyncSessionLocal() as session:
            # Check for duplicate message_id
            existing_result = await session.execute(
                select(InboxMessage).where(InboxMessage.message_id == raw_email.message_id)
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                logger.warning(
                    "email_already_ingested",
                    message_id=raw_email.message_id,
                    inbox_message_id=str(existing.id),
                )
                return {
                    "inbox_message_id": str(existing.id),
                    "attachment_ids": [],
                    "from_email": existing.from_email,
                    "subject": existing.subject,
                    "body_text": existing.body_text,
                    "thread_id": None,
                    "duplicate": True,
                }

            # Extract thread_id from headers
            thread_id = self._extract_thread_id(references_header, in_reply_to_header)

            # Create InboxMessage
            inbox_msg = InboxMessage(
                message_id=raw_email.message_id,
                from_email=raw_email.from_email,
                subject=raw_email.subject,
                body_text=raw_email.body_text,
                received_at=raw_email.received_at,
                status=InboxStatus.NEW,
            )
            session.add(inbox_msg)

            # Persist thread_id if available
            if thread_id:
                inbox_msg.thread_id = thread_id

            await session.flush()  # Get inbox_msg.id
            inbox_message_id = inbox_msg.id

            # Save attachments
            attachment_ids = await self._save_attachments(
                session, inbox_message_id, raw_email.attachments
            )

            await session.commit()

        logger.info(
            "email_ingestion_complete",
            inbox_message_id=str(inbox_message_id),
            attachment_count=len(attachment_ids),
            thread_id=thread_id,
        )

        return {
            "inbox_message_id": str(inbox_message_id),
            "attachment_ids": [str(a) for a in attachment_ids],
            "from_email": raw_email.from_email,
            "subject": raw_email.subject,
            "body_text": raw_email.body_text,
            "original_message_id": raw_email.message_id,
            "thread_id": thread_id,
            "duplicate": False,
        }

    async def _save_attachments(
        self,
        session: AsyncSession,
        inbox_message_id: UUID,
        attachments: list,
    ) -> list[UUID]:
        """Save attachments to disk and create DB records.

        Args:
            session: SQLAlchemy async session
            inbox_message_id: Parent InboxMessage ID
            attachments: List of Attachment dataclass objects

        Returns:
            List of created EmailAttachment UUIDs
        """
        attachment_ids: list[UUID] = []
        if not attachments:
            return attachment_ids

        # Create directory: {UPLOAD_DIR}/attachments/{inbox_message_id}/
        attachment_dir = Path(settings.UPLOAD_DIR) / "attachments" / str(inbox_message_id)
        attachment_dir.mkdir(parents=True, exist_ok=True)

        for attachment in attachments:
            # Sanitize filename
            safe_filename = self._sanitize_filename(attachment.filename)
            file_path = attachment_dir / safe_filename

            # Write to disk
            file_path.write_bytes(attachment.data)

            # Create DB record
            email_attachment = EmailAttachment(
                inbox_message_id=inbox_message_id,
                filename=safe_filename,
                content_type=attachment.content_type,
                file_size=len(attachment.data),
                file_path=str(file_path),
                ocr_status=OCRStatus.PENDING,
            )
            session.add(email_attachment)
            await session.flush()
            attachment_ids.append(email_attachment.id)

            logger.info(
                "attachment_saved",
                attachment_id=str(email_attachment.id),
                filename=safe_filename,
                size_bytes=len(attachment.data),
                path=str(file_path),
            )

        return attachment_ids

    def _extract_thread_id(
        self, references_header: str | None, in_reply_to_header: str | None
    ) -> str | None:
        """Extract thread ID from References or In-Reply-To headers.

        Thread ID is the first message ID in the References chain,
        or the In-Reply-To message ID if References is absent.

        Args:
            references_header: Space-separated message IDs from References header
            in_reply_to_header: Single message ID from In-Reply-To header

        Returns:
            Thread ID (message ID string) or None
        """
        # Try References first (oldest message ID is the thread root)
        if references_header:
            matches = self._THREAD_ID_PATTERN.findall(references_header)
            if matches:
                return matches[0]

        # Fallback to In-Reply-To
        if in_reply_to_header:
            matches = self._THREAD_ID_PATTERN.findall(in_reply_to_header)
            if matches:
                return matches[0]

        return None

    async def process_from_dict(self, raw_email_data: dict) -> dict:
        """Process email from serialized dict (used by Celery tasks).

        Args:
            raw_email_data: Dict with message_id, from_email, subject, body_text,
                received_at, attachments (list of {filename, content_type, data_b64})

        Returns:
            Same as process() output
        """
        import base64
        from datetime import datetime

        from app.integrations.email.imap_client import Attachment, RawEmail

        attachments = []
        for att_data in raw_email_data.get("attachments", []):
            data = att_data.get("data_b64", "")
            if isinstance(data, str):
                data = base64.b64decode(data)
            attachments.append(
                Attachment(
                    filename=att_data["filename"],
                    content_type=att_data.get("content_type", "application/octet-stream"),
                    data=data,
                )
            )

        received_at = raw_email_data.get("received_at")
        if isinstance(received_at, str):
            received_at = datetime.fromisoformat(received_at)
        elif received_at is None:
            received_at = datetime.utcnow()

        raw_email = RawEmail(
            message_id=raw_email_data["message_id"],
            from_email=raw_email_data["from_email"],
            subject=raw_email_data.get("subject", ""),
            body_text=raw_email_data.get("body_text", ""),
            received_at=received_at,
            attachments=attachments,
        )

        return await self.process(
            raw_email=raw_email,
            references_header=raw_email_data.get("references_header"),
            in_reply_to_header=raw_email_data.get("in_reply_to_header"),
        )

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe filesystem storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename (alphanumeric + underscore + dot + extension)
        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")
        # Remove null bytes
        filename = filename.replace("\x00", "")
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[: 255 - len(ext) - 1] + "." + ext
        return filename
