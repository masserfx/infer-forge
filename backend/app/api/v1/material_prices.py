"""Material price management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models import User
from app.models.user import UserRole
from app.schemas import (
    MaterialPriceCreate,
    MaterialPriceImportResult,
    MaterialPriceListResponse,
    MaterialPriceResponse,
    MaterialPriceUpdate,
)
from app.services.material_price import MaterialPriceService

router = APIRouter(prefix="/materialy", tags=["materialy"])


@router.get("", response_model=MaterialPriceListResponse)
async def list_material_prices(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNOLOG, UserRole.OBCHODNIK, UserRole.VEDENI))],
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Maximální počet záznamů"),
    search: str | None = Query(None, description="Vyhledávání v názvu a specifikaci"),
    material_grade: str | None = Query(None, description="Filtr dle třídy materiálu"),
    form: str | None = Query(None, description="Filtr dle formy materiálu"),
    is_active: bool | None = Query(None, description="Filtr dle aktivního stavu"),
) -> MaterialPriceListResponse:
    """Seznam materiálových cen s možností filtrování a vyhledávání."""
    service = MaterialPriceService(db, user_id=current_user.id)
    items, total = await service.get_all(
        skip=skip,
        limit=limit,
        search=search,
        material_grade=material_grade,
        form=form,
        is_active=is_active,
    )

    return MaterialPriceListResponse(
        items=[
            MaterialPriceResponse(
                id=item.id,
                name=item.name,
                specification=item.specification,
                material_grade=item.material_grade,
                form=item.form,
                dimension=item.dimension,
                unit=item.unit,
                unit_price=item.unit_price,
                supplier=item.supplier,
                valid_from=item.valid_from,
                valid_to=item.valid_to,
                is_active=item.is_active,
                notes=item.notes,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
            )
            for item in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/search/best-price", response_model=MaterialPriceResponse | None)
async def search_best_price(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNOLOG, UserRole.OBCHODNIK, UserRole.VEDENI))],
    material_name: str | None = Query(None, description="Název materiálu"),
    material_grade: str | None = Query(None, description="Třída materiálu"),
    dimension: str | None = Query(None, description="Rozměry"),
) -> MaterialPriceResponse | None:
    """Vyhledání nejlepší (nejlevnější platné) ceny pro materiál.

    Priorita vyhledávání:
    1. Přesná shoda třídy materiálu (material_grade)
    2. LIKE shoda názvu (material_name)
    3. Nejlevnější platná cena mezi shodami
    """
    if not material_name and not material_grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zadejte alespoň material_name nebo material_grade",
        )

    service = MaterialPriceService(db, user_id=current_user.id)
    price = await service.find_best_price(
        material_name=material_name,
        material_grade=material_grade,
        dimension=dimension,
    )

    if not price:
        return None

    return MaterialPriceResponse(
        id=price.id,
        name=price.name,
        specification=price.specification,
        material_grade=price.material_grade,
        form=price.form,
        dimension=price.dimension,
        unit=price.unit,
        unit_price=price.unit_price,
        supplier=price.supplier,
        valid_from=price.valid_from,
        valid_to=price.valid_to,
        is_active=price.is_active,
        notes=price.notes,
        created_at=price.created_at.isoformat(),
        updated_at=price.updated_at.isoformat(),
    )


@router.get("/{price_id}", response_model=MaterialPriceResponse)
async def get_material_price(
    price_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNOLOG, UserRole.OBCHODNIK, UserRole.VEDENI))],
) -> MaterialPriceResponse:
    """Detail materiálové ceny."""
    service = MaterialPriceService(db, user_id=current_user.id)
    price = await service.get_by_id(price_id)

    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Materiálová cena nenalezena",
        )

    return MaterialPriceResponse(
        id=price.id,
        name=price.name,
        specification=price.specification,
        material_grade=price.material_grade,
        form=price.form,
        dimension=price.dimension,
        unit=price.unit,
        unit_price=price.unit_price,
        supplier=price.supplier,
        valid_from=price.valid_from,
        valid_to=price.valid_to,
        is_active=price.is_active,
        notes=price.notes,
        created_at=price.created_at.isoformat(),
        updated_at=price.updated_at.isoformat(),
    )


@router.post("", response_model=MaterialPriceResponse, status_code=status.HTTP_201_CREATED)
async def create_material_price(
    data: MaterialPriceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI))],
) -> MaterialPriceResponse:
    """Vytvoření nové materiálové ceny."""
    service = MaterialPriceService(db, user_id=current_user.id)
    price = await service.create(data)
    await db.commit()

    return MaterialPriceResponse(
        id=price.id,
        name=price.name,
        specification=price.specification,
        material_grade=price.material_grade,
        form=price.form,
        dimension=price.dimension,
        unit=price.unit,
        unit_price=price.unit_price,
        supplier=price.supplier,
        valid_from=price.valid_from,
        valid_to=price.valid_to,
        is_active=price.is_active,
        notes=price.notes,
        created_at=price.created_at.isoformat(),
        updated_at=price.updated_at.isoformat(),
    )


@router.put("/{price_id}", response_model=MaterialPriceResponse)
async def update_material_price(
    price_id: UUID,
    data: MaterialPriceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI))],
) -> MaterialPriceResponse:
    """Úprava existující materiálové ceny."""
    service = MaterialPriceService(db, user_id=current_user.id)
    price = await service.update(price_id, data)

    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Materiálová cena nenalezena",
        )

    await db.commit()

    return MaterialPriceResponse(
        id=price.id,
        name=price.name,
        specification=price.specification,
        material_grade=price.material_grade,
        form=price.form,
        dimension=price.dimension,
        unit=price.unit,
        unit_price=price.unit_price,
        supplier=price.supplier,
        valid_from=price.valid_from,
        valid_to=price.valid_to,
        is_active=price.is_active,
        notes=price.notes,
        created_at=price.created_at.isoformat(),
        updated_at=price.updated_at.isoformat(),
    )


@router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_price(
    price_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI))],
) -> None:
    """Smazání materiálové ceny."""
    service = MaterialPriceService(db, user_id=current_user.id)
    success = await service.delete(price_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Materiálová cena nenalezena",
        )

    await db.commit()


@router.post("/import", response_model=MaterialPriceImportResult)
async def import_material_prices(
    file: Annotated[UploadFile, File(description="Excel soubor s cenami materiálů")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNOLOG, UserRole.VEDENI))],
) -> MaterialPriceImportResult:
    """Import materiálových cen z Excel souboru.

    Očekávané sloupce:
    - name (název)
    - specification (specifikace) - volitelné
    - material_grade (třída_materiálu) - volitelné
    - form (forma) - volitelné
    - dimension (rozměry) - volitelné
    - unit (jednotka) - výchozí "kg"
    - unit_price (jednotková_cena)
    - supplier (dodavatel) - volitelné
    - valid_from (platnost_od)
    - valid_to (platnost_do) - volitelné
    - is_active (aktivní) - výchozí True
    - notes (poznámky) - volitelné
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neplatný formát souboru. Očekáván Excel (.xlsx, .xls)",
        )

    content = await file.read()
    service = MaterialPriceService(db, user_id=current_user.id)
    result = await service.import_from_excel(content)

    await db.commit()

    return result
