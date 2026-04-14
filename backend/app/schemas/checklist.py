"""Schemas Pydantic pour les checklists terrain."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Template ---
class ChecklistItemRead(BaseModel):
    id: int
    label: str
    description: Optional[str] = None
    order: int
    ref_code: Optional[str] = None
    model_config = {"from_attributes": True}


class ChecklistSectionRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    order: int
    items: list[ChecklistItemRead] = []
    model_config = {"from_attributes": True}


class ChecklistTemplateRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: str
    is_predefined: bool
    sections: list[ChecklistSectionRead] = []
    model_config = {"from_attributes": True}


class ChecklistTemplateList(BaseModel):
    """Version allégée sans sections/items pour les listes."""

    id: int
    name: str
    description: Optional[str] = None
    category: str
    is_predefined: bool
    model_config = {"from_attributes": True}


# --- Instance ---
class ChecklistInstanceCreate(BaseModel):
    template_id: int
    audit_id: int
    site_id: Optional[int] = None


class ChecklistInstanceRead(BaseModel):
    id: int
    template_id: int
    audit_id: int
    site_id: Optional[int] = None
    filled_by: Optional[int] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Response (réponse à un item) ---
class ChecklistResponseUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(OK|NOK|NA|UNCHECKED)$")
    note: Optional[str] = None


class ChecklistResponseRead(BaseModel):
    id: int
    instance_id: int
    item_id: int
    status: str
    note: Optional[str] = None
    responded_by: Optional[int] = None
    responded_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class ChecklistInstanceDetail(ChecklistInstanceRead):
    """Instance avec toutes les réponses."""

    responses: list[ChecklistResponseRead] = []
    template_name: str = ""
