"""
Routes API pour ORADAD — configuration, analyse et rapports ANSSI.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_auditeur
from ...services.oradad_config_service import OradadConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oradad", tags=["ORADAD"])


# ── Schemas ──────────────────────────────────────────────────────────


class DomainEntry(BaseModel):
    server: str = Field(..., min_length=1, max_length=255, description="IP ou FQDN du DC")
    port: int = Field(default=389, ge=1, le=65535)
    domain_name: str = Field(..., min_length=1, max_length=255, description="ex: client.local")
    username: str = Field(..., min_length=1, max_length=255, description="ex: auditeur")
    user_domain: str = Field(..., min_length=1, max_length=255, description="ex: CLIENT")
    password: str = Field(..., min_length=1, max_length=1000)


class DomainEntryResponse(BaseModel):
    server: str
    port: int
    domain_name: str
    username: str
    user_domain: str


class OradadConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    auto_get_domain: bool = False
    auto_get_trusts: bool = False
    level: int = Field(default=4, ge=1, le=4)
    confidential: int = Field(default=0, ge=0, le=2)
    process_sysvol: bool = True
    sysvol_filter: Optional[str] = Field(default=None, max_length=2000)
    output_files: bool = False
    output_mla: bool = True
    sleep_time: int = Field(default=0, ge=0, le=3600)
    explicit_domains: Optional[list[DomainEntry]] = Field(default=None, max_length=50)


class OradadConfigUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    auto_get_domain: Optional[bool] = None
    auto_get_trusts: Optional[bool] = None
    level: Optional[int] = Field(default=None, ge=1, le=4)
    confidential: Optional[int] = Field(default=None, ge=0, le=2)
    process_sysvol: Optional[bool] = None
    sysvol_filter: Optional[str] = Field(default=None, max_length=2000)
    output_files: Optional[bool] = None
    output_mla: Optional[bool] = None
    sleep_time: Optional[int] = Field(default=None, ge=0)
    explicit_domains: Optional[list[DomainEntry]] = None


class OradadConfigResponse(BaseModel):
    id: int
    name: str
    auto_get_domain: bool
    auto_get_trusts: bool
    level: int
    confidential: int
    process_sysvol: bool
    sysvol_filter: Optional[str] = None
    output_files: bool
    output_mla: bool
    sleep_time: int
    explicit_domains: Optional[list[DomainEntryResponse]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


def _config_to_response(config) -> dict:
    """Convertit un OradadConfig en dict de reponse avec mots de passe masques."""
    return {
        "id": config.id,
        "name": config.name,
        "auto_get_domain": config.auto_get_domain,
        "auto_get_trusts": config.auto_get_trusts,
        "level": config.level,
        "confidential": config.confidential,
        "process_sysvol": config.process_sysvol,
        "sysvol_filter": config.sysvol_filter,
        "output_files": config.output_files,
        "output_mla": config.output_mla,
        "sleep_time": config.sleep_time,
        "explicit_domains": config.get_domains_masked() or None,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


# ── Config CRUD ──────────────────────────────────────────────────────


@router.get("/configs")
def list_configs(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
) -> list[OradadConfigResponse]:
    """Liste les profils de configuration ORADAD du user."""
    configs = OradadConfigService.list_configs(
        db,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return [_config_to_response(c) for c in configs]


@router.post("/configs", status_code=201)
def create_config(
    body: OradadConfigCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
) -> OradadConfigResponse:
    """Cree un profil de configuration ORADAD."""
    config = OradadConfigService.create_config(db, body, owner_id=current_user.id)
    return _config_to_response(config)


@router.put("/configs/{config_id}")
def update_config(
    config_id: int,
    body: OradadConfigUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
) -> OradadConfigResponse:
    """Met a jour un profil de configuration ORADAD."""
    config = OradadConfigService.update_config(
        db,
        config_id,
        body,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return _config_to_response(config)


@router.delete("/configs/{config_id}")
def delete_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Supprime un profil de configuration ORADAD."""
    OradadConfigService.delete_config(
        db,
        config_id,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return {"detail": "Profil supprime"}


@router.post("/configs/{config_id}/generate-xml")
def generate_config_xml(
    config_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Genere le XML config-oradad.xml depuis un profil."""
    config = OradadConfigService.get_config(
        db,
        config_id,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return {"xml": config.to_xml()}


# ── Analysis routes ──────────────────────────────────────────────────


@router.post("/analyze/{task_uuid}")
def analyze_oradad(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """
    Lance l'analyse ANSSI sur les resultats d'une tache ORADAD completee.
    Retourne le rapport ANSSI (findings + score).
    """
    task = OradadConfigService.get_task(
        db,
        task_uuid,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    return OradadConfigService.analyze(db, task)


@router.get("/report/{task_uuid}")
def get_oradad_report(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Retourne le rapport ANSSI d'une tache ORADAD deja analysee."""
    task = OradadConfigService.get_task(
        db,
        task_uuid,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )

    if not task.result_summary or "anssi_report" not in task.result_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun rapport ANSSI disponible",
        )

    return task.result_summary["anssi_report"]


@router.get("/tasks")
def list_oradad_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Liste les taches ORADAD."""
    tasks = OradadConfigService.list_tasks(
        db,
        owner_id=current_user.id,
        is_admin=current_user.role == "admin",
    )

    return [
        {
            "id": t.id,
            "task_uuid": t.task_uuid,
            "agent_name": t.agent.name if t.agent else None,
            "status": t.status,
            "progress": t.progress,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "has_report": bool(t.result_summary and "anssi_report" in t.result_summary),
        }
        for t in tasks
    ]
