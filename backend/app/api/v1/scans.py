"""
Routes Scan Réseau — Lancement de scans Nmap, gestion des résultats,
décisions sur les hosts découverts, import vers équipements.
"""
import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, PaginationParams
from ...models.user import User
from ...models.site import Site
from ...schemas.scan import (
    ScanCreate,
    ScanRead,
    ScanSummary,
    ScanHostRead,
    ScanHostDecision,
)
from ...schemas.common import PaginatedResponse, MessageResponse
from ...core.task_runner import get_task_runner
from ...services import scan_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=ScanRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Lancer un scan réseau (asynchrone)",
)
async def launch_scan(
    payload: ScanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """
    Lance un scan Nmap de manière asynchrone.
    Crée immédiatement un enregistrement en statut 'running' et retourne la réponse.
    Le scan s'exécute en arrière-plan. Utilisez GET /scans pour suivre le statut.
    Plusieurs scans peuvent tourner en parallèle.
    """
    # Vérifier que le site existe
    site = db.get(Site, payload.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    # Valider le type de scan
    valid_types = ("discovery", "port_scan", "full", "custom")
    if payload.scan_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Type de scan invalide. Valeurs possibles : {', '.join(valid_types)}",
        )

    # En mode custom, les arguments personnalisés sont obligatoires
    if payload.scan_type == "custom" and not payload.custom_args:
        raise HTTPException(
            status_code=400,
            detail="Les arguments personnalisés (custom_args) sont obligatoires pour le type 'custom'",
        )

    try:
        # Créer le scan en statut 'running' (retour immédiat)
        scan = scan_service.create_pending_scan(
            db=db,
            site_id=payload.site_id,
            target=payload.target,
            scan_type=payload.scan_type,
            nom=payload.nom,
            notes=payload.notes,
            custom_args=payload.custom_args,
        )

        # Lancer l'exécution en arrière-plan
        task_runner = get_task_runner()
        task_runner.submit(
            scan_service.execute_scan_background,
            scan_id=scan.id,
            site_id=payload.site_id,
            target=payload.target,
            scan_type=payload.scan_type,
            custom_args=payload.custom_args,
        )

        return scan

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Erreur lors de la création du scan")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la création du scan.")


@router.get(
    "/preview-command",
    summary="Aperçu de la commande Nmap",
)
async def preview_nmap_command(
    scan_type: str = Query(..., description="Type de scan"),
    target: str = Query("", description="Cible"),
    custom_args: Optional[str] = Query(None, description="Arguments custom"),
    _: User = Depends(get_current_user),
):
    """Retourne un aperçu de la commande nmap qui sera exécutée."""
    command = scan_service.get_nmap_command_preview(target, scan_type, custom_args)
    return {"command": command}


@router.get(
    "",
    response_model=PaginatedResponse[ScanSummary],
    summary="Lister les scans",
)
async def list_scans(
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les scans réseau, optionnellement filtrés par site."""
    items, total = scan_service.list_scans(
        db, site_id=site_id, skip=pagination.offset, limit=pagination.page_size
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=math.ceil(total / pagination.page_size) if total > 0 else 1,
    )


@router.get(
    "/{scan_id}",
    response_model=ScanRead,
    summary="Détails d'un scan",
)
async def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Récupère les détails d'un scan avec tous les hosts et ports."""
    scan = scan_service.get_scan_with_hosts(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    return scan


@router.delete(
    "/{scan_id}",
    response_model=MessageResponse,
    summary="Supprimer un scan",
)
async def delete_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Supprime un scan et tous ses résultats."""
    if not scan_service.delete_scan(db, scan_id):
        raise HTTPException(status_code=404, detail="Scan introuvable")
    return MessageResponse(message="Scan supprimé")


# ── Host management ──

@router.put(
    "/hosts/{host_id}/decision",
    response_model=ScanHostRead,
    summary="Décider du sort d'un host découvert",
)
async def decide_host(
    host_id: int,
    payload: ScanHostDecision,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """
    Met à jour la décision sur un host :
    - kept : conserver (optionnellement créer un équipement)
    - ignored : ignorer ce host
    """
    if payload.decision not in ("kept", "ignored"):
        raise HTTPException(
            status_code=400,
            detail="Décision invalide. Valeurs possibles : kept, ignored",
        )

    try:
        host = scan_service.update_host_decision(
            db=db,
            host_id=host_id,
            decision=payload.decision,
            chosen_type=payload.chosen_type,
            hostname_override=payload.hostname,
            create_equipement=payload.create_equipement,
        )
        return host
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/hosts/{host_id}/link/{equipement_id}",
    response_model=ScanHostRead,
    summary="Lier un host à un équipement existant",
)
async def link_host(
    host_id: int,
    equipement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Lie un host découvert à un équipement existant dans la base."""
    try:
        host = scan_service.link_host_to_equipement(db, host_id, equipement_id)
        return host
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/{scan_id}/import-all",
    response_model=MessageResponse,
    summary="Importer tous les hosts en attente",
)
async def import_all_hosts(
    scan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """
    Crée automatiquement un équipement pour chaque host 'pending'
    d'un scan. Le type est deviné en fonction des ports et de l'OS.
    """
    try:
        created = scan_service.import_all_kept_hosts(db, scan_id)
        return MessageResponse(
            message=f"{len(created)} équipement(s) créé(s)",
            detail=f"IPs : {', '.join(e.ip_address for e in created)}" if created else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
