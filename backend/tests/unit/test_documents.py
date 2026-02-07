"""Unit tests for Document Management module."""

import uuid
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import (
    AuditAction,
    AuditLog,
    Document,
    DocumentCategory,
)
from app.schemas import DocumentResponse, DocumentUpdate, DocumentUpload
from app.services import DocumentService


@pytest.fixture
def upload_dir(tmp_path: Path) -> Path:
    """Create temporary upload directory for tests."""
    upload_path = tmp_path / "uploads"
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


@pytest.fixture
def test_settings(upload_dir: Path) -> Settings:
    """Create test settings with temp upload directory."""
    settings = Settings(
        DEBUG=True,
        SECRET_KEY="test_secret_key_not_for_production",
        ANTHROPIC_API_KEY="test_key",
        MAX_UPLOAD_SIZE_MB=10,
    )
    # Override UPLOAD_DIR directly to avoid validation
    settings.UPLOAD_DIR = str(upload_dir)
    return settings


@pytest.fixture
def mock_settings(test_settings: Settings) -> Generator[Settings, None, None]:
    """Mock get_settings to return test_settings."""
    with patch("app.services.document.get_settings", return_value=test_settings):
        yield test_settings


class TestDocumentModel:
    """Tests for Document model."""

    async def test_create_document_minimal_fields(self, test_db: AsyncSession) -> None:
        """Test creating Document with minimal required fields."""
        doc = Document(
            entity_type="order",
            entity_id=uuid.uuid4(),
            file_name="test.pdf",
            file_path="/uploads/order/test.pdf",
            mime_type="application/pdf",
        )
        test_db.add(doc)
        await test_db.flush()
        await test_db.refresh(doc)

        assert doc.id is not None
        assert doc.file_name == "test.pdf"
        assert doc.version == 1  # default
        assert doc.file_size == 0  # default
        assert doc.category == DocumentCategory.OSTATNI  # default
        assert doc.created_at is not None
        assert doc.updated_at is not None

    async def test_document_category_enum_values(self) -> None:
        """Test DocumentCategory enum has expected values."""
        categories = [
            DocumentCategory.VYKRES,
            DocumentCategory.ATESTACE,
            DocumentCategory.WPS,
            DocumentCategory.PRUVODKA,
            DocumentCategory.FAKTURA,
            DocumentCategory.NABIDKA,
            DocumentCategory.OBJEDNAVKA,
            DocumentCategory.PROTOKOL,
            DocumentCategory.OSTATNI,
        ]
        assert len(categories) == 9
        assert DocumentCategory.VYKRES.value == "vykres"
        assert DocumentCategory.ATESTACE.value == "atestace"

    async def test_document_version_defaults_to_one(self, test_db: AsyncSession) -> None:
        """Test version defaults to 1."""
        doc = Document(
            entity_type="customer",
            entity_id=uuid.uuid4(),
            file_name="contract.pdf",
            file_path="/path/contract.pdf",
            mime_type="application/pdf",
        )
        test_db.add(doc)
        await test_db.flush()

        assert doc.version == 1

    async def test_file_size_defaults_to_zero(self, test_db: AsyncSession) -> None:
        """Test file_size defaults to 0."""
        doc = Document(
            entity_type="offer",
            entity_id=uuid.uuid4(),
            file_name="offer.xlsx",
            file_path="/path/offer.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        test_db.add(doc)
        await test_db.flush()

        assert doc.file_size == 0

    async def test_category_defaults_to_ostatni(self, test_db: AsyncSession) -> None:
        """Test category defaults to OSTATNI."""
        doc = Document(
            entity_type="order",
            entity_id=uuid.uuid4(),
            file_name="note.txt",
            file_path="/path/note.txt",
            mime_type="text/plain",
        )
        test_db.add(doc)
        await test_db.flush()

        assert doc.category == DocumentCategory.OSTATNI

    async def test_relationship_with_entity_type_and_id(
        self, test_db: AsyncSession
    ) -> None:
        """Test Document can be linked to any entity via entity_type + entity_id."""
        entity_id = uuid.uuid4()
        doc1 = Document(
            entity_type="order",
            entity_id=entity_id,
            file_name="drawing.pdf",
            file_path="/path/drawing.pdf",
            mime_type="application/pdf",
            category=DocumentCategory.VYKRES,
        )
        doc2 = Document(
            entity_type="order",
            entity_id=entity_id,
            file_name="certificate.pdf",
            file_path="/path/certificate.pdf",
            mime_type="application/pdf",
            category=DocumentCategory.ATESTACE,
        )

        test_db.add_all([doc1, doc2])
        await test_db.flush()

        # Both documents should reference same entity
        assert doc1.entity_type == doc2.entity_type
        assert doc1.entity_id == doc2.entity_id


class TestDocumentService:
    """Tests for DocumentService."""

    async def test_upload_document_creates_file_and_record(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test upload creates both file on disk and DB record."""
        service = DocumentService(test_db, user_id=uuid.uuid4())
        entity_id = uuid.uuid4()
        metadata = DocumentUpload(
            entity_type="order",
            entity_id=entity_id,
            category=DocumentCategory.VYKRES,
            description="Technical drawing",
        )
        file_content = b"PDF content here"

        document = await service.upload(
            metadata=metadata,
            file_name="drawing.pdf",
            file_content=file_content,
            mime_type="application/pdf",
        )

        assert document.id is not None
        assert document.file_name == "drawing.pdf"
        assert document.mime_type == "application/pdf"
        assert document.file_size == len(file_content)
        assert document.category == DocumentCategory.VYKRES
        assert document.description == "Technical drawing"
        assert document.version == 1
        assert document.uploaded_by == service.user_id

        # Check file exists on disk
        file_path = Path(document.file_path)
        assert file_path.exists()
        assert file_path.read_bytes() == file_content

    async def test_upload_with_automatic_versioning(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test uploading same file_name creates version 2."""
        service = DocumentService(test_db)
        entity_id = uuid.uuid4()
        metadata = DocumentUpload(
            entity_type="order",
            entity_id=entity_id,
        )

        # First upload - version 1
        doc1 = await service.upload(
            metadata=metadata,
            file_name="spec.pdf",
            file_content=b"Version 1 content",
            mime_type="application/pdf",
        )

        # Second upload with same name - version 2
        doc2 = await service.upload(
            metadata=metadata,
            file_name="spec.pdf",
            file_content=b"Version 2 content",
            mime_type="application/pdf",
        )

        assert doc1.version == 1
        assert doc2.version == 2
        assert doc1.id != doc2.id  # Different documents
        assert doc1.file_path != doc2.file_path  # Different files on disk

    async def test_upload_rejects_too_large_file(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test upload rejects file exceeding MAX_UPLOAD_SIZE_MB."""
        service = DocumentService(test_db)
        metadata = DocumentUpload(
            entity_type="order",
            entity_id=uuid.uuid4(),
        )

        # Create content larger than 10MB (test limit)
        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB

        with pytest.raises(ValueError, match="exceeds maximum"):
            await service.upload(
                metadata=metadata,
                file_name="huge.pdf",
                file_content=large_content,
                mime_type="application/pdf",
            )

    async def test_upload_rejects_invalid_mime_type(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test upload rejects MIME type not in ALLOWED_MIME_TYPES."""
        service = DocumentService(test_db)
        metadata = DocumentUpload(
            entity_type="order",
            entity_id=uuid.uuid4(),
        )

        with pytest.raises(ValueError, match="MIME type .* is not allowed"):
            await service.upload(
                metadata=metadata,
                file_name="malware.exe",
                file_content=b"executable content",
                mime_type="application/x-executable",
            )

    async def test_get_by_id_existing_document(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_by_id returns existing document."""
        service = DocumentService(test_db)
        metadata = DocumentUpload(
            entity_type="customer",
            entity_id=uuid.uuid4(),
        )

        created = await service.upload(
            metadata=metadata,
            file_name="contract.pdf",
            file_content=b"contract text",
            mime_type="application/pdf",
        )

        found = await service.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id
        assert found.file_name == "contract.pdf"

    async def test_get_by_id_nonexistent_returns_none(
        self,
        test_db: AsyncSession,
    ) -> None:
        """Test get_by_id returns None for non-existent document."""
        service = DocumentService(test_db)
        result = await service.get_by_id(uuid.uuid4())
        assert result is None

    async def test_get_by_entity_returns_documents(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_by_entity returns documents for specific entity."""
        service = DocumentService(test_db)
        entity_id = uuid.uuid4()

        # Upload 3 documents for same entity
        for i in range(3):
            await service.upload(
                metadata=DocumentUpload(
                    entity_type="order",
                    entity_id=entity_id,
                ),
                file_name=f"doc{i}.pdf",
                file_content=b"content",
                mime_type="application/pdf",
            )

        # Upload 1 document for different entity (should not appear)
        await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
            ),
            file_name="other.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        documents = await service.get_by_entity("order", entity_id)
        assert len(documents) == 3

    async def test_get_by_entity_with_category_filter(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_by_entity filters by category."""
        service = DocumentService(test_db)
        entity_id = uuid.uuid4()

        # Upload 2 VYKRES, 1 ATESTACE
        await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=entity_id,
                category=DocumentCategory.VYKRES,
            ),
            file_name="drawing1.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )
        await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=entity_id,
                category=DocumentCategory.VYKRES,
            ),
            file_name="drawing2.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )
        await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=entity_id,
                category=DocumentCategory.ATESTACE,
            ),
            file_name="cert.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        vykres_docs = await service.get_by_entity(
            "order", entity_id, category=DocumentCategory.VYKRES
        )
        assert len(vykres_docs) == 2

        atestace_docs = await service.get_by_entity(
            "order", entity_id, category=DocumentCategory.ATESTACE
        )
        assert len(atestace_docs) == 1

    async def test_get_all_no_filters(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_all returns all documents."""
        service = DocumentService(test_db)

        # Upload 2 documents for different entities
        for i in range(2):
            await service.upload(
                metadata=DocumentUpload(
                    entity_type="order",
                    entity_id=uuid.uuid4(),
                ),
                file_name=f"doc{i}.pdf",
                file_content=b"content",
                mime_type="application/pdf",
            )

        documents = await service.get_all()
        assert len(documents) == 2

    async def test_get_all_with_entity_type_filter(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_all filters by entity_type."""
        service = DocumentService(test_db)

        # Upload 1 order doc, 1 customer doc
        await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
            ),
            file_name="order.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )
        await service.upload(
            metadata=DocumentUpload(
                entity_type="customer",
                entity_id=uuid.uuid4(),
            ),
            file_name="customer.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        order_docs = await service.get_all(entity_type="order")
        assert len(order_docs) == 1
        assert order_docs[0].entity_type == "order"

    async def test_get_all_with_category_filter(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_all filters by category."""
        service = DocumentService(test_db)

        # Upload VYKRES and FAKTURA
        await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
                category=DocumentCategory.VYKRES,
            ),
            file_name="drawing.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )
        await service.upload(
            metadata=DocumentUpload(
                entity_type="customer",
                entity_id=uuid.uuid4(),
                category=DocumentCategory.FAKTURA,
            ),
            file_name="invoice.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        faktura_docs = await service.get_all(category=DocumentCategory.FAKTURA)
        assert len(faktura_docs) == 1
        assert faktura_docs[0].category == DocumentCategory.FAKTURA

    async def test_update_category(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test updating document category."""
        service = DocumentService(test_db)
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
                category=DocumentCategory.OSTATNI,
            ),
            file_name="doc.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        updated = await service.update(
            doc.id,
            DocumentUpdate(category=DocumentCategory.ATESTACE),
        )

        assert updated is not None
        assert updated.category == DocumentCategory.ATESTACE

    async def test_update_description(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test updating document description."""
        service = DocumentService(test_db)
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
                description="Old description",
            ),
            file_name="doc.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        updated = await service.update(
            doc.id,
            DocumentUpdate(description="New description"),
        )

        assert updated is not None
        assert updated.description == "New description"

    async def test_update_nonexistent_returns_none(
        self,
        test_db: AsyncSession,
    ) -> None:
        """Test update returns None for non-existent document."""
        service = DocumentService(test_db)
        result = await service.update(
            uuid.uuid4(),
            DocumentUpdate(description="Won't work"),
        )
        assert result is None

    async def test_delete_removes_db_record_and_file(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test delete removes both DB record and file from disk."""
        service = DocumentService(test_db)
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
            ),
            file_name="todelete.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        file_path = Path(doc.file_path)
        assert file_path.exists()

        result = await service.delete(doc.id)
        assert result is True

        # Check DB record gone
        found = await service.get_by_id(doc.id)
        assert found is None

        # Check file gone
        assert not file_path.exists()

    async def test_delete_nonexistent_returns_false(
        self,
        test_db: AsyncSession,
    ) -> None:
        """Test delete returns False for non-existent document."""
        service = DocumentService(test_db)
        result = await service.delete(uuid.uuid4())
        assert result is False

    async def test_delete_by_entity_removes_all_documents(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test delete_by_entity removes all documents for entity."""
        service = DocumentService(test_db)
        entity_id = uuid.uuid4()

        # Upload 3 documents
        for i in range(3):
            await service.upload(
                metadata=DocumentUpload(
                    entity_type="order",
                    entity_id=entity_id,
                ),
                file_name=f"doc{i}.pdf",
                file_content=b"content",
                mime_type="application/pdf",
            )

        # Delete all
        count = await service.delete_by_entity("order", entity_id)
        assert count == 3

        # Check none left
        remaining = await service.get_by_entity("order", entity_id)
        assert len(remaining) == 0

    async def test_get_file_content_returns_document_and_bytes(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_file_content returns document metadata and file bytes."""
        service = DocumentService(test_db)
        content = b"File content for download"
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
            ),
            file_name="download.pdf",
            file_content=content,
            mime_type="application/pdf",
        )

        result = await service.get_file_content(doc.id)
        assert result is not None
        document, file_bytes = result
        assert document.id == doc.id
        assert file_bytes == content

    async def test_get_file_content_nonexistent_file_returns_none(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test get_file_content returns None when file missing from disk."""
        service = DocumentService(test_db)
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
            ),
            file_name="willdelete.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        # Delete file from disk manually (simulating corruption)
        Path(doc.file_path).unlink()

        result = await service.get_file_content(doc.id)
        assert result is None

    async def test_audit_trail_on_create(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test audit log created on document upload."""
        user_id = uuid.uuid4()
        service = DocumentService(test_db, user_id=user_id)
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
                category=DocumentCategory.VYKRES,
            ),
            file_name="audit_test.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        # Fetch audit log
        from sqlalchemy import select

        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "document",
                AuditLog.entity_id == doc.id,
                AuditLog.action == AuditAction.CREATE,
            )
        )
        audit = result.scalar_one_or_none()

        assert audit is not None
        assert audit.user_id == user_id
        assert audit.changes is not None
        assert audit.changes["file_name"] == "audit_test.pdf"
        assert audit.changes["category"] == "vykres"
        assert audit.changes["version"] == 1

    async def test_audit_trail_on_update(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test audit log created on document update."""
        user_id = uuid.uuid4()
        service = DocumentService(test_db, user_id=user_id)
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
                category=DocumentCategory.OSTATNI,
            ),
            file_name="update_test.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        # Update category
        await service.update(
            doc.id,
            DocumentUpdate(category=DocumentCategory.ATESTACE),
        )

        # Fetch audit log
        from sqlalchemy import select

        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "document",
                AuditLog.entity_id == doc.id,
                AuditLog.action == AuditAction.UPDATE,
            )
        )
        audit = result.scalar_one_or_none()

        assert audit is not None
        assert audit.user_id == user_id
        assert audit.changes is not None
        assert "category" in audit.changes
        assert audit.changes["category"]["old"] == "ostatni"
        assert audit.changes["category"]["new"] == "atestace"

    async def test_audit_trail_on_delete(
        self,
        test_db: AsyncSession,
        mock_settings: Settings,
    ) -> None:
        """Test audit log created on document delete."""
        user_id = uuid.uuid4()
        service = DocumentService(test_db, user_id=user_id)
        doc = await service.upload(
            metadata=DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
            ),
            file_name="delete_test.pdf",
            file_content=b"content",
            mime_type="application/pdf",
        )

        doc_id = doc.id
        await service.delete(doc_id)

        # Fetch audit log
        from sqlalchemy import select

        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "document",
                AuditLog.entity_id == doc_id,
                AuditLog.action == AuditAction.DELETE,
            )
        )
        audit = result.scalar_one_or_none()

        assert audit is not None
        assert audit.user_id == user_id
        assert audit.changes is not None
        assert audit.changes["deleted_file"] == "delete_test.pdf"


class TestDocumentSchemas:
    """Tests for Document Pydantic schemas."""

    def test_document_upload_validation(self) -> None:
        """Test DocumentUpload schema validation."""
        entity_id = uuid.uuid4()
        upload = DocumentUpload(
            entity_type="order",
            entity_id=entity_id,
            category=DocumentCategory.VYKRES,
            description="Test drawing",
        )

        assert upload.entity_type == "order"
        assert upload.entity_id == entity_id
        assert upload.category == DocumentCategory.VYKRES
        assert upload.description == "Test drawing"

    def test_document_update_partial_update(self) -> None:
        """Test DocumentUpdate allows partial updates (all optional)."""
        # Update only category
        update1 = DocumentUpdate(category=DocumentCategory.FAKTURA)
        assert update1.category == DocumentCategory.FAKTURA
        assert update1.description is None

        # Update only description
        update2 = DocumentUpdate(description="Updated description")
        assert update2.category is None
        assert update2.description == "Updated description"

        # Update both
        update3 = DocumentUpdate(
            category=DocumentCategory.ATESTACE,
            description="New cert",
        )
        assert update3.category == DocumentCategory.ATESTACE
        assert update3.description == "New cert"

    async def test_document_response_from_attributes(self, test_db: AsyncSession) -> None:
        """Test DocumentResponse can be created from model instance."""
        doc = Document(
            entity_type="order",
            entity_id=uuid.uuid4(),
            file_name="test.pdf",
            file_path="/uploads/test.pdf",
            mime_type="application/pdf",
            file_size=1024,
            version=2,
            category=DocumentCategory.VYKRES,
            description="Technical drawing",
        )
        test_db.add(doc)
        await test_db.flush()
        await test_db.refresh(doc)

        response = DocumentResponse.model_validate(doc)
        assert response.file_name == "test.pdf"
        assert response.category == DocumentCategory.VYKRES
        assert response.version == 2
        assert response.file_size == 1024

    def test_document_category_validation(self) -> None:
        """Test DocumentCategory enum validates correctly."""
        # Valid category
        upload = DocumentUpload(
            entity_type="order",
            entity_id=uuid.uuid4(),
            category=DocumentCategory.WPS,
        )
        assert upload.category == DocumentCategory.WPS

        # Invalid category should raise validation error
        with pytest.raises(ValueError):
            DocumentUpload(
                entity_type="order",
                entity_id=uuid.uuid4(),
                category="invalid_category",  # type: ignore[arg-type, unused-ignore]
            )

    def test_invalid_entity_type_length(self) -> None:
        """Test entity_type validates max length (50)."""
        # Valid length
        upload = DocumentUpload(
            entity_type="a" * 50,  # exactly 50 chars
            entity_id=uuid.uuid4(),
        )
        assert len(upload.entity_type) == 50

        # Exceeds limit - should fail validation
        with pytest.raises(ValueError):
            DocumentUpload(
                entity_type="a" * 51,
                entity_id=uuid.uuid4(),
            )
