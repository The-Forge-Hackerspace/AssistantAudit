"""
Routes API pour l'analyse ORADAD — verification des donnees AD
contre le referentiel ANSSI.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_auditeur
from ...models.agent_task import AgentTask
from ...services.oradad_analysis_service import OradadAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oradad", tags=["ORADAD"])


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

    # Ownership: owner or admin
    if task.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tache ORADAD introuvable",
        )

    return task


# ── Routes ───────────────────────────────────────────────────────────


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

    # Already analyzed — return cached report
    if task.result_summary and "anssi_report" in task.result_summary:
        return task.result_summary["anssi_report"]

    # Parse raw result (tar data stored as raw bytes or base64 in result_raw)
    if not task.result_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune donnee brute disponible pour cette tache",
        )

    try:
        # result_raw may be raw bytes or a file path — attempt direct bytes first
        raw_bytes = task.result_raw.encode("utf-8") if isinstance(task.result_raw, str) else task.result_raw
        parsed_data = OradadAnalysisService.parse_oradad_tar(raw_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Run ANSSI checks against parsed AD data
    findings = OradadAnalysisService.run_anssi_checks(db, parsed_data)

    # Calculate overall score
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

    # Persist report in result_summary
    summary = dict(task.result_summary) if task.result_summary else {}
    summary["anssi_report"] = report
    task.result_summary = summary
    db.commit()

    logger.info(
        "Analyse ANSSI terminee pour la tache %s — score: %s, level: %s",
        task_uuid,
        report["score"],
        report["level"],
    )

    return report


@router.get("/report/{task_uuid}")
def get_oradad_report(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """
    Retourne le rapport ANSSI d'une tache ORADAD deja analysee.
    """
    task = _get_task_or_404(db, task_uuid, current_user)

    if not task.result_summary or "anssi_report" not in task.result_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun rapport ANSSI disponible — lancez d'abord POST /oradad/analyze/{task_uuid}",
        )

    return task.result_summary["anssi_report"]


@router.get("/tasks")
def list_oradad_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_auditeur),
):
    """
    Liste les taches ORADAD. Admin voit toutes les taches,
    auditeur voit uniquement les siennes.
    """
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
