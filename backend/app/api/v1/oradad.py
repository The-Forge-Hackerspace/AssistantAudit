"""
Routes API pour ORADAD — configuration, analyse et rapports ANSSI.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from ...core.database import get_db
from ...core.deps import get_current_auditeur
from ...models.agent_task import AgentTask
from ...models.oradad_config import OradadConfig
from ...services.oradad_analysis_service import OradadAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oradad", tags=["ORADAD"])


# ── Schemas ──────────────────────────────────────────────────────────


class OradadConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    auto_get_domain: bool = True
    auto_get_trusts: bool = True
    level: int = Field(default=4, ge=1, le=4)
    confidential: int = Field(default=0, ge=0, le=2)
    process_sysvol: bool = True
    sysvol_filter: Optional[str] = None
    output_files: bool = False
    output_mla: bool = True
    sleep_time: int = Field(default=0, ge=0)
    explicit_domains: Optional[list[dict]] = None


class OradadConfigUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    auto_get_domain: Optional[bool] = None
    auto_get_trusts: Optional[bool] = None
    level: Optional[int] = Field(default=None, ge=1, le=4)
    confidential: Optional[int] = Field(default=None, ge=0, le=2)
    process_sysvol: Optional[bool] = None
    sysvol_filter: Optional[str] = None
    output_files: Optional[bool] = None
    output_mla: Optional[bool] = None
    sleep_time: Optional[int] = Field(default=None, ge=0)
    explicit_domains: Optional[list[dict]] = None


class OradadConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

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
    explicit_domains: Optional[list[dict]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ── Helpers ──────────────────────────────────────────────────────────


def _get_task_or_404(
    db: Session,
    task_uuid: str,
    current_user,
) -> AgentTask:
    """Recupere une AgentTask oradad et verifie l'ownership."""
    task = db.query(AgentTask).filter(
        AgentTask.task_uuid == task_uuid,
        AgentTask.tool == "oradad",
    ).first()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tache ORADAD introuvable",
        )

    if task.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tache ORADAD introuvable",
        )

    return task


def _get_config_or_404(
    db: Session,
    config_id: int,
    current_user,
) -> OradadConfig:
    """Recupere un OradadConfig et verifie l'ownership."""
    config = db.query(OradadConfig).filter(OradadConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="Profil de configuration introuvable")
    if config.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=404, detail="Profil de configuration introuvable")
    return config


# ── Config CRUD ──────────────────────────────────────────────────────


@router.get("/configs")
def list_configs(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
) -> list[OradadConfigResponse]:
    """Liste les profils de configuration ORADAD du user."""
    query = db.query(OradadConfig)
    if current_user.role != "admin":
        query = query.filter(OradadConfig.owner_id == current_user.id)
    configs = query.order_by(OradadConfig.created_at.desc()).all()
    return [OradadConfigResponse.model_validate(c) for c in configs]


@router.post("/configs", status_code=201)
def create_config(
    body: OradadConfigCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
) -> OradadConfigResponse:
    """Cree un profil de configuration ORADAD."""
    config = OradadConfig(
        name=body.name,
        owner_id=current_user.id,
        auto_get_domain=body.auto_get_domain,
        auto_get_trusts=body.auto_get_trusts,
        level=body.level,
        confidential=body.confidential,
        process_sysvol=body.process_sysvol,
        sysvol_filter=body.sysvol_filter,
        output_files=body.output_files,
        output_mla=body.output_mla,
        sleep_time=body.sleep_time,
        explicit_domains=body.explicit_domains,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return OradadConfigResponse.model_validate(config)


@router.put("/configs/{config_id}")
def update_config(
    config_id: int,
    body: OradadConfigUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
) -> OradadConfigResponse:
    """Met a jour un profil de configuration ORADAD."""
    config = _get_config_or_404(db, config_id, current_user)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return OradadConfigResponse.model_validate(config)


@router.delete("/configs/{config_id}")
def delete_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Supprime un profil de configuration ORADAD."""
    config = _get_config_or_404(db, config_id, current_user)
    db.delete(config)
    db.commit()
    return {"detail": "Profil supprime"}


@router.post("/configs/{config_id}/generate-xml")
def generate_config_xml(
    config_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Genere le XML config-oradad.xml depuis un profil."""
    config = _get_config_or_404(db, config_id, current_user)
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
    task = _get_task_or_404(db, task_uuid, current_user)

    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La tache n'est pas terminee (status: {task.status})",
        )

    if task.result_summary and "anssi_report" in task.result_summary:
        return task.result_summary["anssi_report"]

    if not task.result_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune donnee brute disponible pour cette tache",
        )

    try:
        raw_bytes = task.result_raw.encode("utf-8") if isinstance(task.result_raw, str) else task.result_raw
        parsed_data = OradadAnalysisService.parse_oradad_tar(raw_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    findings = OradadAnalysisService.run_anssi_checks(db, parsed_data)
    score = OradadAnalysisService.calculate_score(findings)

    report = {
        "findings": findings,
        "score": score["score"],
        "level": score["level"],
        "stats": {
            "total_checks": score["total_checks"],
            "passed": score["passed"],
            "failed": score["failed"],
            "warning": score["warning"],
            "not_checked": score["not_checked"],
        },
    }

    summary = dict(task.result_summary) if task.result_summary else {}
    summary["anssi_report"] = report
    task.result_summary = summary
    db.commit()

    logger.info(
        "Analyse ANSSI terminee pour la tache %s — score: %s, level: %s",
        task_uuid, report["score"], report["level"],
    )

    return report


@router.get("/report/{task_uuid}")
def get_oradad_report(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """Retourne le rapport ANSSI d'une tache ORADAD deja analysee."""
    task = _get_task_or_404(db, task_uuid, current_user)

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
    query = db.query(AgentTask).filter(AgentTask.tool == "oradad")
    if current_user.role != "admin":
        query = query.filter(AgentTask.owner_id == current_user.id)
    tasks = query.order_by(AgentTask.created_at.desc()).all()

    return [
        {
            "id": t.id,
            "task_uuid": t.task_uuid,
            "agent_name": t.agent.name if t.agent else None,
            "status": t.status,
            "progress": t.progress,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "has_report": bool(
                t.result_summary and "anssi_report" in t.result_summary
            ),
        }
        for t in tasks
    ]
