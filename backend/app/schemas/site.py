"""
Schémas Site — Emplacements physiques d'une entreprise.
"""
from typing import Optional

from pydantic import BaseModel, Field


class SiteBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=200)
    adresse: Optional[str] = None


class SiteCreate(SiteBase):
    entreprise_id: int


class SiteUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, max_length=200)
    adresse: Optional[str] = None


class SiteRead(SiteBase):
    id: int
    entreprise_id: int
    equipement_count: int = 0

    model_config = {"from_attributes": True}
