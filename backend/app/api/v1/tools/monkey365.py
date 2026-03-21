import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_auditeur
from ....models.entreprise import Entreprise
from ....models.user import User
from ....schemas.scan import (
    Monkey365ScanCreate,
    Monkey365ScanResultRead,
    Monkey365ScanResultSummary,
)
from ....schemas.common import MessageResponse
from ....services.monkey365_scan_service import Monkey365ScanService

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

