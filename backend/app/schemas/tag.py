"""Schemas Pydantic pour les tags."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#6B7280", max_length=20, pattern=r"^#[0-9a-fA-F]{6}$")
    scope: str = Field(default="global", pattern=r"^(global|audit)$")
    audit_id: Optional[int] = None


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, max_length=20, pattern=r"^#[0-9a-fA-F]{6}$")


class TagRead(TagBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TagAssociationCreate(BaseModel):
    tag_id: int
    taggable_type: str = Field(..., pattern=r"^(equipement|control_result|checklist_response|scan_host)$")
    taggable_id: int


class TagAssociationRead(BaseModel):
    id: int
    tag_id: int
    taggable_type: str
    taggable_id: int
    tag: TagRead

    model_config = {"from_attributes": True}
