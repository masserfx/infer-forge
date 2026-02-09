"""Document API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.core.config import get_settings
from app.integrations.ocr.drawing_analyzer import DrawingAnalyzer
from app.integrations.ocr.processor import OCRProcessor
from app.models import DocumentCategory
from app.models.user import User, UserRole
from app.schemas import DocumentResponse, DocumentUpdate, DocumentUpload
from app.schemas.document_generator import (
    GenerateDeliveryNoteRequest,
    GenerateInvoiceRequest,
    GenerateOfferRequest,
    GenerateOrderConfirmationRequest,
    GenerateProductionSheetRequest,
)
from app.schemas.drawing import (
    DrawingAnalysisResponse,
    DrawingDimensionSchema,
    DrawingMaterialSchema,
    DrawingToleranceSchema,
    WeldingRequirementsSchema,
)
from app.services import DocumentGeneratorService, DocumentService

router = APIRouter(prefix="/dokumenty", tags=["Dokumenty"])


async def _persist_generated_document(
    db: AsyncSession,
    order_id: UUID,
    pdf_bytes: bytes,
    file_name: str,
    category: DocumentCategory,
    description: str,
) -> None:
    """Save a generated PDF to disk and create a Document record in the DB."""
    service = DocumentService(db)
    metadata = DocumentUpload(
        entity_type="order",
        entity_id=order_id,
        category=category,
        description=description,
    )
    await service.upload(
        metadata=metadata,
        file_name=file_name,
        file_content=pdf_bytes,
        mime_type="application/pdf",
    )
    await db.commit()


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


@router.get("/{document_id}/analysis")
async def get_drawing_analysis(
    document_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get cached drawing analysis results for a document."""
    from sqlalchemy import select as sql_select
    from app.models.drawing_analysis import DrawingAnalysis

    result = await db.execute(
        sql_select(DrawingAnalysis).where(DrawingAnalysis.document_id == document_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found for document {document_id}",
        )

    return {
        "document_id": str(document_id),
        "dimensions": analysis.dimensions or [],
        "materials": analysis.materials or [],
        "tolerances": analysis.tolerances or [],
        "surface_treatments": analysis.surface_treatments or [],
        "welding_requirements": analysis.welding_requirements or {},
        "notes": analysis.notes or [],
        "analyzed_at": str(analysis.created_at) if hasattr(analysis, 'created_at') else None,
    }


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
        file_name = f"nabidka_{order_id}.pdf"
        await _persist_generated_document(
            db, order_id, pdf_bytes, file_name,
            DocumentCategory.NABIDKA, "Vygenerovaná nabídka",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
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
        file_name = f"pruvodka_{order_id}.pdf"
        await _persist_generated_document(
            db, order_id, pdf_bytes, file_name,
            DocumentCategory.PRUVODKA, "Vygenerovaná výrobní průvodka",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/{document_id}/analyze-drawing", response_model=DrawingAnalysisResponse)
async def analyze_drawing(
    document_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> DrawingAnalysisResponse:
    """Analyze technical drawing and extract structured data.

    Runs OCR on the document file and then uses AI to extract dimensions,
    materials, tolerances, surface treatments, and welding requirements.

    Requires TECHNOLOG or VEDENI role.
    """
    settings = get_settings()

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key not configured",
        )

    # Get document and file content
    service = DocumentService(db)
    result = await service.get_file_content(document_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or file missing",
        )

    document, file_content = result

    # Save to temporary file for OCR
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(
        suffix=Path(document.file_name).suffix,
        delete=False,
    ) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name

    try:
        # Run OCR
        ocr_processor = OCRProcessor(language="ces+eng")
        ocr_result = await ocr_processor.extract_text(tmp_path)

        if not ocr_result.text or not ocr_result.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text could be extracted from document via OCR",
            )

        # Run drawing analysis
        analyzer = DrawingAnalyzer(api_key=settings.ANTHROPIC_API_KEY)
        analysis = await analyzer.analyze(ocr_result.text)

        # Convert to response schema
        return DrawingAnalysisResponse(
            dimensions=[
                DrawingDimensionSchema(
                    type=dim.type,
                    value=dim.value,
                    unit=dim.unit,
                    tolerance=dim.tolerance,
                )
                for dim in analysis.dimensions
            ],
            materials=[
                DrawingMaterialSchema(
                    grade=mat.grade,
                    standard=mat.standard,
                    type=mat.type,
                )
                for mat in analysis.materials
            ],
            tolerances=[
                DrawingToleranceSchema(
                    type=tol.type,
                    value=tol.value,
                    standard=tol.standard,
                )
                for tol in analysis.tolerances
            ],
            surface_treatments=analysis.surface_treatments,
            welding_requirements=WeldingRequirementsSchema(
                wps=analysis.welding_requirements.wps,
                wpqr=analysis.welding_requirements.wpqr,
                ndt_methods=analysis.welding_requirements.ndt_methods,
                acceptance_criteria=analysis.welding_requirements.acceptance_criteria,
            ),
            notes=analysis.notes,
        )

    finally:
        # Clean up temporary file
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/generate/dimensional-protocol/{order_id}")
async def generate_dimensional_protocol(
    order_id: UUID,
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate dimensional protocol PDF for an order."""
    service = DocumentGeneratorService(db)
    try:
        pdf_bytes = await service.generate_dimensional_protocol(order_id=order_id)

        # Fetch order number for filename
        from sqlalchemy import select as sql_select

        from app.models.order import Order

        result = await db.execute(sql_select(Order.number).where(Order.id == order_id))
        order_number = result.scalar_one_or_none() or str(order_id)

        file_name = f"protokol_rozmerovy_{order_number}.pdf"
        await _persist_generated_document(
            db, order_id, pdf_bytes, file_name,
            DocumentCategory.PROTOKOL, "Vygenerovaný rozměrový protokol",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/generate/material-certificate/{order_id}")
async def generate_material_certificate(
    order_id: UUID,
    certificate_type: str = Query(default="3.1", regex="^(3\\.1|3\\.2)$"),
    _user: User = Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate material certificate PDF for an order (EN 10-204).

    Args:
        order_id: Order UUID.
        certificate_type: Certificate type ("3.1" or "3.2"). Defaults to "3.1".
    """
    service = DocumentGeneratorService(db)
    try:
        pdf_bytes = await service.generate_material_certificate(
            order_id=order_id,
            certificate_type=certificate_type,
        )

        # Fetch order number for filename
        from sqlalchemy import select as sql_select

        from app.models.order import Order

        result = await db.execute(sql_select(Order.number).where(Order.id == order_id))
        order_number = result.scalar_one_or_none() or str(order_id)

        cert_type_filename = certificate_type.replace(".", "")
        file_name = f"atestace_{cert_type_filename}_{order_number}.pdf"
        await _persist_generated_document(
            db, order_id, pdf_bytes, file_name,
            DocumentCategory.ATESTACE, f"Vygenerovaná atestace EN 10-204 {certificate_type}",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/generate/invoice/{order_id}")
async def generate_invoice_pdf(
    order_id: UUID,
    request: GenerateInvoiceRequest | None = None,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate invoice PDF for an order."""
    service = DocumentGeneratorService(db)
    req = request or GenerateInvoiceRequest()
    try:
        pdf_bytes = await service.generate_invoice_pdf(
            order_id=order_id,
            invoice_type=req.invoice_type,
            due_days=req.due_days,
            note=req.note,
        )
        file_name = f"faktura_{order_id}.pdf"
        await _persist_generated_document(
            db, order_id, pdf_bytes, file_name,
            DocumentCategory.FAKTURA, "Vygenerovaná faktura",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/generate/delivery-note/{order_id}")
async def generate_delivery_note(
    order_id: UUID,
    request: GenerateDeliveryNoteRequest | None = None,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.TECHNOLOG, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate delivery note PDF for an order."""
    service = DocumentGeneratorService(db)
    req = request or GenerateDeliveryNoteRequest()
    try:
        pdf_bytes = await service.generate_delivery_note_pdf(
            order_id=order_id,
            delivery_address=req.delivery_address,
            note=req.note,
        )
        file_name = f"dodaci_list_{order_id}.pdf"
        await _persist_generated_document(
            db, order_id, pdf_bytes, file_name,
            DocumentCategory.OSTATNI, "Vygenerovaný dodací list",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/generate/order-confirmation/{order_id}")
async def generate_order_confirmation(
    order_id: UUID,
    request: GenerateOrderConfirmationRequest | None = None,
    _user: User = Depends(require_role(UserRole.OBCHODNIK, UserRole.VEDENI)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate order confirmation PDF for an order."""
    service = DocumentGeneratorService(db)
    req = request or GenerateOrderConfirmationRequest()
    try:
        pdf_bytes = await service.generate_order_confirmation_pdf(
            order_id=order_id,
            show_prices=req.show_prices,
            delivery_terms=req.delivery_terms,
            payment_terms=req.payment_terms,
            note=req.note,
        )
        file_name = f"objednavka_{order_id}.pdf"
        await _persist_generated_document(
            db, order_id, pdf_bytes, file_name,
            DocumentCategory.OBJEDNAVKA, "Vygenerované potvrzení objednávky",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
