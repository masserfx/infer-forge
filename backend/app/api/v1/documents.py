"""Document API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models import DocumentCategory
from app.models.user import User, UserRole
from app.schemas import DocumentResponse, DocumentUpdate, DocumentUpload
from app.schemas.document_generator import GenerateOfferRequest, GenerateProductionSheetRequest
from app.services import DocumentGeneratorService, DocumentService

router = APIRouter(prefix="/dokumenty", tags=["Dokumenty"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(..., description="File to upload"),
    entity_type: str = Form(..., description="Entity type (order, customer, offer)"),
    entity_id: UUID = Form(..., description="Entity UUID"),
    category: DocumentCategory = Form(
        default=DocumentCategory.OSTATNI, description="Document category"
    ),
    description: str | None = Form(None, description="Document description"),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a document file."""
    service = DocumentService(db)

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    metadata = DocumentUpload(
        entity_type=entity_type,
        entity_id=entity_id,
        category=category,
        description=description,
    )

    try:
        document = await service.upload(
            metadata=metadata,
            file_name=file.filename or "unnamed",
            file_content=content,
            mime_type=file.content_type or "application/octet-stream",
        )
        await db.commit()
        return DocumentResponse.model_validate(document)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    category: DocumentCategory | None = Query(None, description="Filter by category"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List all documents with optional filters."""
    service = DocumentService(db)
    documents = await service.get_all(
        entity_type=entity_type,
        category=category,
        skip=skip,
        limit=limit,
    )
    return [DocumentResponse.model_validate(d) for d in documents]


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[DocumentResponse])
async def get_entity_documents(
    entity_type: str,
    entity_id: UUID,
    category: DocumentCategory | None = Query(None, description="Filter by category"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Get documents for a specific entity."""
    service = DocumentService(db)
    documents = await service.get_by_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        category=category,
        skip=skip,
        limit=limit,
    )
    return [DocumentResponse.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get document metadata by ID."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download document file."""
    service = DocumentService(db)
    result = await service.get_file_content(document_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or file missing",
        )

    document, content = result
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.file_name}"',
            "Content-Length": str(document.file_size),
        },
    )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    update_data: DocumentUpdate,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Update document metadata."""
    service = DocumentService(db)
    document = await service.update(document_id, update_data)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    await db.commit()
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document (file and DB record)."""
    service = DocumentService(db)
    deleted = await service.delete(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    await db.commit()


@router.post("/generate/offer/{order_id}")
async def generate_offer(
    order_id: UUID,
    request: GenerateOfferRequest | None = None,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate offer PDF for an order."""
    service = DocumentGeneratorService(db)
    req = request or GenerateOfferRequest()
    try:
        pdf_bytes = await service.generate_offer_pdf(
            order_id=order_id,
            valid_days=req.valid_days,
            note=req.note,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="nabidka_{order_id}.pdf"',
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/generate/production-sheet/{order_id}")
async def generate_production_sheet(
    order_id: UUID,
    request: GenerateProductionSheetRequest | None = None,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate production sheet PDF for an order."""
    service = DocumentGeneratorService(db)
    req = request or GenerateProductionSheetRequest()
    try:
        pdf_bytes = await service.generate_production_sheet_pdf(
            order_id=order_id,
            include_controls=req.include_controls,
            note=req.note,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="pruvodka_{order_id}.pdf"',
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
