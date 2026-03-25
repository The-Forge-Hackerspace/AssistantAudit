import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_auditeur
from ....models.entreprise import Entreprise
from ....models.user import User
from ....schemas.scan import (
    Monkey365ScanCreate,
    Monkey365ScanResultRead,
    Monkey365ScanResultSummary,
    Monkey365ScanLogs,
    Monkey365ImportRequest,
    Monkey365ImportResult,
)
from ....schemas.common import MessageResponse
from ....services.monkey365_scan_service import Monkey365ScanService
from ....services.assessment_service import AssessmentService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/monkey365/run", response_model=Monkey365ScanResultSummary, status_code=201)
async def launch_monkey365_scan(
    request: Monkey365ScanCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    entreprise = db.get(Entreprise, request.entreprise_id)
    if not entreprise:
        raise HTTPException(404, f"Entreprise #{request.entreprise_id} introuvable")

    try:
        result = Monkey365ScanService.launch_scan(
            db=db,
            entreprise_id=request.entreprise_id,
            config=request.config,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.exception("Unexpected error launching monkey365 scan")
        raise HTTPException(500, f"Erreur interne: {e}")

    logger.info(
        f"Monkey365 scan #{result.id} lancé en background "
        f"(entreprise={request.entreprise_id})"
    )
    return result


@router.get("/monkey365/scans/{entreprise_id}", response_model=list[Monkey365ScanResultSummary])
async def list_monkey365_scans(
    entreprise_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    return Monkey365ScanService.list_scans(
        db=db,
        entreprise_id=entreprise_id,
    )


@router.get("/monkey365/scans/result/{result_id}", response_model=Monkey365ScanResultRead)
async def get_monkey365_scan_result(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    result = Monkey365ScanService.get_scan(db, result_id)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    return result


@router.get("/monkey365/scans/result/{result_id}/logs", response_model=Monkey365ScanLogs)
async def get_monkey365_scan_logs(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Retourne les dernières lignes du log PowerShell du scan (lecture directe du fichier)."""
    result = Monkey365ScanService.get_scan(db, result_id)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    if not result.output_path:
        return Monkey365ScanLogs(lines=[], total_lines=0)
    log_file = Path(result.output_path) / "monkey365.log"
    if not log_file.exists():
        return Monkey365ScanLogs(lines=[], total_lines=0)
    try:
        content = log_file.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        return Monkey365ScanLogs(lines=lines[-500:], total_lines=len(lines))
    except Exception:
        return Monkey365ScanLogs(lines=[], total_lines=0)


@router.post("/monkey365/scans/{result_id}/cancel", response_model=Monkey365ScanResultSummary)
async def cancel_monkey365_scan(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Force l'arrêt d'un scan bloqué en statut RUNNING."""
    result = Monkey365ScanService.get_scan(db, result_id)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    if result.status != "running":
        raise HTTPException(400, "Ce scan n'est pas en cours d'exécution")

    from datetime import datetime, timezone
    from app.models.monkey365_scan_result import Monkey365ScanStatus
    result.status = Monkey365ScanStatus.FAILED
    result.completed_at = datetime.now(timezone.utc)
    result.error_message = "Scan annulé manuellement"
    db.commit()
    db.refresh(result)
    return result


@router.get("/monkey365/scans/result/{result_id}/report")
async def get_monkey365_scan_report(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Retourne le fichier HTML du rapport Monkey365."""
    result = Monkey365ScanService.get_scan(db, result_id)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    if result.status != "success":
        raise HTTPException(400, "Rapport disponible uniquement pour les scans réussis")

    output_path = Path(result.output_path) if result.output_path else None
    html_file: Path | None = None

    if output_path and output_path.exists():
        html_dir = output_path / "HTML"
        if html_dir.exists():
            candidates = sorted(html_dir.glob("*.html"))
            if candidates:
                html_file = candidates[0]

    if not html_file:
        raise HTTPException(404, "Fichier HTML introuvable pour ce scan")

    return FileResponse(
        path=str(html_file),
        media_type="text/html",
        filename=html_file.name,
    )


@router.post("/monkey365/scans/{result_id}/import-to-audit", response_model=Monkey365ImportResult, status_code=201)
async def import_monkey365_to_audit(
    result_id: int,
    request: Monkey365ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Importe un scan Monkey365 réussi dans un audit existant (crée campagne + assessment CIS-M365-V5)."""
    try:
        result = AssessmentService.import_monkey365_scan(
            db=db,
            scan_result_id=result_id,
            audit_id=request.audit_id,
            assessed_by=current_user.username,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Erreur lors de l'import Monkey365 vers l'audit")
        raise HTTPException(500, f"Erreur interne: {e}")

    return Monkey365ImportResult(**result)


@router.delete("/monkey365/scans/{result_id}", response_model=MessageResponse)
async def delete_monkey365_scan(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime un audit Monkey365 et nettoie les fichiers associés."""
    if not Monkey365ScanService.delete_scan(db, result_id):
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    return MessageResponse(message=f"Audit Monkey365 #{result_id} supprimé")

