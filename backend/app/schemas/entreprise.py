"""
Schémas Entreprise & Contact.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Contact ---
class ContactBase(BaseModel):
    nom: str = Field(..., max_length=200)
    role: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=200)
    telephone: Optional[str] = Field(default=None, max_length=20)
    is_main_contact: bool = False


class ContactCreate(ContactBase):
    pass


class ContactRead(ContactBase):
    id: int
    entreprise_id: int

    model_config = {"from_attributes": True}


# --- Entreprise ---
class EntrepriseBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=200)
    adresse: Optional[str] = None
    secteur_activite: Optional[str] = None
    siret: Optional[str] = Field(default=None, max_length=14)
    presentation_desc: Optional[str] = None
    contraintes_reglementaires: Optional[str] = None


class EntrepriseCreate(EntrepriseBase):
    contacts: list[ContactCreate] = []


class EntrepriseUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, max_length=200)
    adresse: Optional[str] = None
    secteur_activite: Optional[str] = None
    siret: Optional[str] = None
    presentation_desc: Optional[str] = None
    contraintes_reglementaires: Optional[str] = None


class EntrepriseRead(EntrepriseBase):
    id: int
    owner_id: int
    created_at: datetime
    contacts: list[ContactRead] = []

    model_config = {"from_attributes": True}
