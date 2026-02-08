"""Pydantic schemas for document generation."""

from pydantic import BaseModel


class GenerateOfferRequest(BaseModel):
    """Optional overrides for offer generation."""

    valid_days: int = 30
    note: str | None = None


class GenerateProductionSheetRequest(BaseModel):
    """Optional overrides for production sheet generation."""

    include_controls: bool = True
    note: str | None = None
