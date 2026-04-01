import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_auditeur
from ....core.helpers import user_has_access_to_entreprise
from ....core.task_runner import get_task_runner
from ....models.entreprise import Entreprise
from ....models.monkey365_scan_result import Monkey365ScanStatus
from ....models.user import User
from ....schemas.common import MessageResponse
from ....schemas.scan import (
    Monkey365ImportRequest,
    Monkey365ImportResult,
    Monkey365ScanCreate,
    Monkey365ScanLogs,
    Monkey365ScanResultRead,
    Monkey365ScanResultSummary,
    Monkey365StreamingScanCreate,
    Monkey365StreamingScanResponse,
)
from ....services.assessment_service import AssessmentService
from ....services.monkey365_scan_service import Monkey365ScanService

logger = logging.getLogger(__name__)
router = APIRouter()


def _rbac(u: User) -> tuple[int, bool]:
    return u.id, u.role == "admin"


@router.post("/monkey365/run", response_model=Monkey365ScanResultSummary, status_code=201)
def launch_monkey365_scan(
    request: Monkey365ScanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    uid, adm = _rbac(current_user)
    entreprise = db.get(Entreprise, request.entreprise_id)
    if not entreprise:
        raise HTTPException(404, f"Entreprise #{request.entreprise_id} introuvable")
    if not adm and not user_has_access_to_entreprise(db, request.entreprise_id, uid):
        raise HTTPException(404, "Ressource introuvable")

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

    # Commit avant de lancer le thread background, sinon la nouvelle session
    # du thread ne verra pas le scan (transaction pas encore commitée).
    db.commit()

    task_runner = get_task_runner()
    task_runner.submit(
        Monkey365ScanService.execute_scan_background,
        result.id,
        request.config.model_dump(),
    )
    logger.info(
        "Monkey365 scan #%s lancé en background (entreprise=%s)",
        result.id, request.entreprise_id,
    )
    return result


@router.get("/monkey365/scans/{entreprise_id}", response_model=list[Monkey365ScanResultSummary])
def list_monkey365_scans(
    entreprise_id: int,
    page: int = Query(1, ge=1, description="Numéro de page, commence à 1"),
    page_size: int = Query(50, ge=1, le=500, description="Nombre de résultats par page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Liste paginée des audits Monkey365 pour une entreprise."""
    uid, adm = _rbac(current_user)
    return Monkey365ScanService.list_scans(
        db=db,
        entreprise_id=entreprise_id,
        skip=(page - 1) * page_size,
        limit=page_size,
        user_id=uid, is_admin=adm,
    )


@router.get("/monkey365/scans/result/{result_id}", response_model=Monkey365ScanResultRead)
def get_monkey365_scan_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    uid, adm = _rbac(current_user)
    result = Monkey365ScanService.get_scan(db, result_id, user_id=uid, is_admin=adm)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    return result


@router.get("/monkey365/scans/result/{result_id}/logs", response_model=Monkey365ScanLogs)
def get_monkey365_scan_logs(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Retourne les dernières lignes du log PowerShell du scan (lecture directe du fichier)."""
    uid, adm = _rbac(current_user)
    result = Monkey365ScanService.get_scan(db, result_id, user_id=uid, is_admin=adm)
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
        if tail_start > 0 and len(lines) > 1:
            lines = lines[1:]
        return Monkey365ScanLogs(lines=lines[-500:], total_lines=len(lines))
    except OSError as exc:
        logger.warning("Impossible de lire le fichier de logs %s: %s", log_file, exc)
        return Monkey365ScanLogs(lines=[], total_lines=0)


@router.post("/monkey365/scans/{result_id}/cancel", response_model=Monkey365ScanResultSummary)
def cancel_monkey365_scan(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Force l'arrêt d'un scan en cours : tue le process PowerShell et met le status à CANCELLED."""
    uid, adm = _rbac(current_user)
    result = Monkey365ScanService.get_scan(db, result_id, user_id=uid, is_admin=adm)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    if result.status not in (Monkey365ScanStatus.RUNNING, Monkey365ScanStatus.AUTHENTICATING):
        raise HTTPException(400, "Ce scan n'est pas en cours d'exécution")

    Monkey365ScanService.kill_scan_process(result_id)

    result.status = Monkey365ScanStatus.CANCELLED
    result.completed_at = datetime.now(timezone.utc)
    result.error_message = "Scan annulé manuellement"
    db.flush()
    db.refresh(result)
    return result


@router.get("/monkey365/scans/result/{result_id}/report")
def get_monkey365_scan_report(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Retourne le fichier HTML du rapport Monkey365."""
    uid, adm = _rbac(current_user)
    result = Monkey365ScanService.get_scan(db, result_id, user_id=uid, is_admin=adm)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    if result.status != Monkey365ScanStatus.SUCCESS:
        raise HTTPException(400, "Rapport disponible uniquement pour les scans réussis")

    if not result.output_path:
        raise HTTPException(404, "Fichier HTML introuvable pour ce scan")

    html_file: Path | None = None
    output_root = Path(result.output_path)
    if output_root.exists():
        # Monkey365 crée un sous-dossier avec son propre UUID,
        # donc on cherche récursivement dans l'arborescence.
        candidates = sorted(output_root.rglob("*.html"))
        if candidates:
            html_file = candidates[0]

    if not html_file:
        raise HTTPException(404, "Fichier HTML introuvable pour ce scan")

    return FileResponse(
        path=str(html_file),
        media_type="text/html",
        filename=html_file.name,
        headers={"Content-Disposition": f'inline; filename="{html_file.name}"'},
    )


@router.post("/monkey365/scans/{result_id}/import-to-audit", response_model=Monkey365ImportResult, status_code=201)
def import_monkey365_to_audit(
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


@router.post("/monkey365/stream", response_model=Monkey365StreamingScanResponse, status_code=201)
async def launch_monkey365_streaming_scan(
    request: Monkey365StreamingScanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """
    Lance un scan Monkey365 en mode streaming avec Device Code Flow.
    """
    uid, adm = _rbac(current_user)
    entreprise = db.get(Entreprise, request.entreprise_id)
    if not entreprise:
        raise HTTPException(404, "Ressource introuvable")

    if not adm and not user_has_access_to_entreprise(db, request.entreprise_id, uid):
        raise HTTPException(404, "Ressource introuvable")

    try:
        result = Monkey365ScanService.create_streaming_scan(
            db=db,
            entreprise_id=request.entreprise_id,
            tenant_id=request.tenant_id,
            auth_method=request.auth_method.value,
            config=request.config,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    asyncio.create_task(
        Monkey365ScanService.execute_streaming_scan(
            result_id=result.id,
            user_id=current_user.id,
            tenant_id=request.tenant_id,
            subscriptions=request.subscriptions,
            ruleset=request.ruleset,
            auth_method_str=request.auth_method.value,
        )
    )

    logger.info(
        "[MONKEY365-STREAM] Scan #%s lance (user=%s, entreprise=%s)",
        result.id, current_user.id, request.entreprise_id,
    )
    return Monkey365StreamingScanResponse(
        id=result.id,
        scan_id=result.scan_id,
        status=result.status.value,
        auth_method=result.auth_method,
    )


@router.delete("/monkey365/scans/{result_id}", response_model=MessageResponse)
def delete_monkey365_scan(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Supprime un audit Monkey365 et nettoie les fichiers associés."""
    uid, adm = _rbac(current_user)
    if not Monkey365ScanService.delete_scan(db, result_id, user_id=uid, is_admin=adm):
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    return MessageResponse(message=f"Audit Monkey365 #{result_id} supprimé")
