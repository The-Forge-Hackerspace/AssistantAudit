"""
Schémas Framework (Référentiel) & Control.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Control ---
class ControlBase(BaseModel):
    ref_id: str = Field(..., max_length=50)
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    severity: str = Field(default="medium", pattern=r"^(critical|high|medium|low|info)$")
    check_type: str = Field(default="manual", pattern=r"^(manual|automatic|semi-automatic)$")
    order: int = 0
    auto_check_function: Optional[str] = None
    engine_rule_id: Optional[str] = None
    cis_reference: Optional[str] = None
    remediation: Optional[str] = None
    evidence_required: bool = False


class ControlCreate(ControlBase):
    pass


class ControlRead(ControlBase):
    id: int
    category_id: int

    model_config = {"from_attributes": True}


# --- Category ---
class CategoryBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    order: int = 0


class CategoryCreate(CategoryBase):
    controls: list[ControlCreate] = []


class CategoryRead(CategoryBase):
    id: int
    framework_id: int
    controls: list[ControlRead] = []

    model_config = {"from_attributes": True}


# --- Framework ---
class FrameworkBase(BaseModel):
    ref_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    version: str = Field(default="1.0", max_length=20)
    engine: Optional[str] = None
    engine_config: Optional[dict] = None
    source: Optional[str] = Field(None, max_length=500, description="Recommandations sur lesquelles le framework est basé")
    author: Optional[str] = Field(None, max_length=200, description="Créateur du framework")


class FrameworkCreate(FrameworkBase):
    categories: list[CategoryCreate] = []


class FrameworkRead(FrameworkBase):
    id: int
    is_active: bool
    source_file: Optional[str] = None
    parent_version_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    categories: list[CategoryRead] = []
    total_controls: int = 0

    model_config = {"from_attributes": True}


class FrameworkSummary(BaseModel):
    """Version allégée sans les catégories/contrôles"""
    id: int
    ref_id: str
    name: str
    version: str
    engine: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    is_active: bool
    parent_version_id: Optional[int] = None
    total_controls: int = 0

    model_config = {"from_attributes": True}


class FrameworkCloneRequest(BaseModel):
    """Demande de clonage d'un framework en nouvelle version"""
    new_version: str = Field(..., max_length=20, description="Numéro de la nouvelle version")
    new_name: Optional[str] = Field(None, max_length=200, description="Nouveau nom (optionnel)")
