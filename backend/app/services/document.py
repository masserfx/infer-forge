"""Document business logic service."""

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import AuditAction, AuditLog, Document, DocumentCategory
from app.schemas import DocumentUpdate, DocumentUpload

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing documents with file storage and audit trail."""

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/dwg",
        "application/dxf",
        "image/vnd.dwg",
        "image/vnd.dxf",
        "text/plain",
        "application/xml",
        "text/xml",
    }

    def __init__(self, db: AsyncSession, user_id: Optional[UUID] = None):
        self.db = db
        self.user_id = user_id
        self.settings = get_settings()

    async def _create_audit_log(
        self,
        action: AuditAction,
        entity_id: UUID,
        changes: Optional[dict] = None,
    ) -> None:
        audit = AuditLog(
            user_id=self.user_id,
            action=action,
            entity_type="document",
            entity_id=entity_id,
            changes=changes,
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(audit)

    def _get_upload_path(self, entity_type: str, entity_id: UUID) -> Path:
        """Get upload directory path for entity."""
        base = Path(self.settings.UPLOAD_DIR)
        return base / entity_type / str(entity_id)

    def _validate_file_size(self, file_size: int) -> None:
        """Validate file size against configured maximum."""
        max_bytes = self.settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(
                f"File size {file_size} exceeds maximum "
                f"{self.settings.MAX_UPLOAD_SIZE_MB} MB"
            )

    async def upload(
        self,
        metadata: DocumentUpload,
        file_name: str,
        file_content: bytes,
        mime_type: str,
    ) -> Document:
        """Upload a document file and create DB record.

        Args:
            metadata: Upload metadata (entity_type, entity_id, category)
            file_name: Original file name
            file_content: File content bytes
            mime_type: MIME type of the file

        Returns:
            Created Document instance

        Raises:
            ValueError: If file size exceeds limit or MIME type not allowed
        """
        file_size = len(file_content)
        self._validate_file_size(file_size)

        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(f"MIME type '{mime_type}' is not allowed")

        # Create upload directory
        upload_dir = self._get_upload_path(metadata.entity_type, metadata.entity_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique file name to prevent collisions
        file_ext = Path(file_name).suffix
        stored_name = f"{uuid4().hex}{file_ext}"
        file_path = upload_dir / stored_name

        # Write file to disk
        file_path.write_bytes(file_content)

        # Check existing version
        existing = await self._get_latest_version(
            metadata.entity_type, metadata.entity_id, file_name
        )
        version = (existing.version + 1) if existing else 1

        # Create DB record
        document = Document(
            entity_type=metadata.entity_type,
            entity_id=metadata.entity_id,
            file_name=file_name,
            file_path=str(file_path),
            mime_type=mime_type,
            file_size=file_size,
            version=version,
            category=metadata.category,
            description=metadata.description,
            uploaded_by=self.user_id,
        )
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)

        # Audit trail
        await self._create_audit_log(
            action=AuditAction.CREATE,
            entity_id=document.id,
            changes={
                "file_name": file_name,
                "entity_type": metadata.entity_type,
                "entity_id": str(metadata.entity_id),
                "category": metadata.category.value,
                "version": version,
                "file_size": file_size,
            },
        )

        logger.info(
            "document_uploaded file_name=%s entity_type=%s entity_id=%s",
            file_name,
            metadata.entity_type,
            metadata.entity_id,
        )

        return document

    async def _get_latest_version(
        self,
        entity_type: str,
        entity_id: UUID,
        file_name: str,
    ) -> Optional[Document]:
        """Get the latest version of a document by name."""
        result = await self.db.execute(
            select(Document)
            .where(
                Document.entity_type == entity_type,
                Document.entity_id == entity_id,
                Document.file_name == file_name,
            )
            .order_by(Document.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        """Get document by ID."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_file_content(self, document_id: UUID) -> Optional[tuple[Document, bytes]]:
        """Get document metadata and file content for download.

        Returns:
            Tuple of (Document, file_bytes) or None if not found
        """
        document = await self.get_by_id(document_id)
        if not document:
            return None

        file_path = Path(document.file_path)
        if not file_path.exists():
            logger.warning(
                "document_file_missing document_id=%s path=%s",
                document_id,
                document.file_path,
            )
            return None

        file_content = file_path.read_bytes()
        return document, file_content

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        category: Optional[DocumentCategory] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents for an entity with optional category filter."""
        query = (
            select(Document)
            .where(
                Document.entity_type == entity_type,
                Document.entity_id == entity_id,
            )
        )

        if category:
            query = query.where(Document.category == category)

        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all(
        self,
        entity_type: Optional[str] = None,
        category: Optional[DocumentCategory] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get all documents with optional filters."""
        query = select(Document)

        if entity_type:
            query = query.where(Document.entity_type == entity_type)
        if category:
            query = query.where(Document.category == category)

        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        document_id: UUID,
        update_data: DocumentUpdate,
    ) -> Optional[Document]:
        """Update document metadata."""
        document = await self.get_by_id(document_id)
        if not document:
            return None

        changes: dict = {}
        for field, value in update_data.model_dump(exclude_unset=True).items():
            old_value = getattr(document, field)
            new_value = value.value if hasattr(value, "value") else value
            old_str = old_value.value if hasattr(old_value, "value") else str(old_value)
            if old_str != str(new_value):
                changes[field] = {"old": old_str, "new": str(new_value)}
                setattr(document, field, value)

        if changes:
            await self.db.flush()
            await self.db.refresh(document)

            await self._create_audit_log(
                action=AuditAction.UPDATE,
                entity_id=document.id,
                changes=changes,
            )

        return document

    async def delete(self, document_id: UUID) -> bool:
        """Delete document (DB record and file)."""
        document = await self.get_by_id(document_id)
        if not document:
            return False

        # Audit trail before deletion
        await self._create_audit_log(
            action=AuditAction.DELETE,
            entity_id=document.id,
            changes={
                "deleted_file": document.file_name,
                "entity_type": document.entity_type,
                "entity_id": str(document.entity_id),
                "category": document.category.value,
            },
        )

        # Delete file from disk
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        await self.db.delete(document)
        await self.db.flush()

        logger.info(
            "document_deleted document_id=%s file_name=%s",
            document_id,
            document.file_name,
        )

        return True

    async def delete_by_entity(self, entity_type: str, entity_id: UUID) -> int:
        """Delete all documents for an entity. Returns count of deleted documents."""
        documents = await self.get_by_entity(entity_type, entity_id, limit=10000)

        for document in documents:
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()

            await self._create_audit_log(
                action=AuditAction.DELETE,
                entity_id=document.id,
                changes={
                    "deleted_file": document.file_name,
                    "bulk_delete": True,
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                },
            )

            await self.db.delete(document)

        await self.db.flush()

        # Cleanup empty directory
        upload_dir = self._get_upload_path(entity_type, entity_id)
        if upload_dir.exists() and not any(upload_dir.iterdir()):
            shutil.rmtree(upload_dir, ignore_errors=True)

        return len(documents)
