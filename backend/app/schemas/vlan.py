"""Schémas VLAN — Définitions de VLANs par site."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VlanDefinitionCreate(BaseModel):
    site_id: int
    vlan_id: int = Field(..., ge=1, le=4094, description="VLAN ID (1-4094)")
    name: str = Field(..., min_length=1, max_length=100)
    subnet: Optional[str] = Field(default=None, max_length=50)
    color: str = Field(default="#6b7280", pattern=r"^#[0-9a-fA-F]{6}$", max_length=7)
    description: Optional[str] = None


class VlanDefinitionUpdate(BaseModel):
    vlan_id: Optional[int] = Field(default=None, ge=1, le=4094)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    subnet: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$", max_length=7)
    description: Optional[str] = None


class VlanDefinitionRead(BaseModel):
    id: int
    site_id: int
    vlan_id: int
    name: str
    subnet: Optional[str] = None
    color: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
