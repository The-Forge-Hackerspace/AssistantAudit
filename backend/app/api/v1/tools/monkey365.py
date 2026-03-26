import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_auditeur
from ....models.entreprise import Entreprise
from ....models.monkey365_scan_result import Monkey365ScanStatus
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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(
        Monkey365ScanService.execute_scan_background,
        result.id,
        request.config.model_dump(),
    )
    logger.info(
        f"Monkey365 scan #{result.id} lancé en background "
        f"(entreprise={request.entreprise_id})"
    )
    return result


@router.get("/monkey365/scans/{entreprise_id}", response_model=list[Monkey365ScanResultSummary])
async def list_monkey365_scans(
    entreprise_id: int,
    page: int = Query(1, ge=1, description="Numéro de page, commence à 1"),
    page_size: int = Query(50, ge=1, le=500, description="Nombre de résultats par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste paginée des audits Monkey365 pour une entreprise."""
    return Monkey365ScanService.list_scans(
        db=db,
        entreprise_id=entreprise_id,
        skip=(page - 1) * page_size,
        limit=page_size,
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
    LOG_TAIL_BYTES = 50 * 1024
    try:
        with log_file.open("rb") as fh:
            fh.seek(0, 2)
            file_size = fh.tell()
            tail_start = max(0, file_size - LOG_TAIL_BYTES)
            fh.seek(tail_start)
            raw = fh.read()
        content = raw.decode("utf-8", errors="replace")
        lines = content.splitlines()
        # Discard potentially partial first line when reading from the middle
        if tail_start > 0 and len(lines) > 1:
            lines = lines[1:]
        return Monkey365ScanLogs(lines=lines[-500:], total_lines=len(lines))
    except OSError as exc:
        logger.warning("Impossible de lire le fichier de logs %s: %s", log_file, exc)
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
    if result.status != Monkey365ScanStatus.RUNNING:
        raise HTTPException(400, "Ce scan n'est pas en cours d'exécution")

    result.status = Monkey365ScanStatus.CANCELLED
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
    if result.status != Monkey365ScanStatus.SUCCESS:
        raise HTTPException(400, "Rapport disponible uniquement pour les scans réussis")

    if not result.output_path:
        raise HTTPException(404, "Fichier HTML introuvable pour ce scan")

    html_file: Path | None = None
    output_root = Path(result.output_path)
    if output_root.exists():
        for html_dir_name in ("html", "HTML"):
            html_dir = output_root / html_dir_name
            if html_dir.exists():
                candidates = sorted(html_dir.glob("*.html"))
                if candidates:
                    html_file = candidates[0]
                    break

    if not html_file:
        raise HTTPException(404, "Fichier HTML introuvable pour ce scan")

    return FileResponse(
        path=str(html_file),
        media_type="text/html",
        filename=html_file.name,
        headers={"Content-Disposition": f'attachment; filename="{html_file.name}"'},
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

