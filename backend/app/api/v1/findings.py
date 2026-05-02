"""Endpoints API — Findings (non-conformités)."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.deps import PaginationParams, RbacContext, get_db, get_rbac_context
from ...schemas.common import PaginatedResponse
from ...schemas.finding import (
    FindingCountsByStatus,
    FindingDetail,
    FindingGenerateRequest,
    FindingGenerateResponse,
    FindingLinkDuplicate,
    FindingResponse,
    FindingStatusUpdate,
)
from ...services.finding_service import FindingService

router = APIRouter()


# ── Liste des findings ──────────────────────────────────────────────
@router.get("", response_model=PaginatedResponse[FindingResponse])
def list_findings(
    assessment_id: int | None = Query(None, description="Filtrer par assessment"),
    equipment_id: int | None = Query(None, description="Filtrer par équipement"),
    finding_status: str | None = Query(None, alias="status", description="Filtrer par statut"),
    severity: str | None = Query(None, description="Filtrer par sévérité"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Liste les findings avec filtres et pagination."""
    uid, is_admin = rbac.user_id, rbac.is_admin
    findings, total = FindingService.list_findings(
        db,
        assessment_id=assessment_id,
        equipment_id=equipment_id,
        status=finding_status,
        severity=severity,
        offset=pagination.offset,
        limit=pagination.page_size,
        user_id=uid,
        is_admin=is_admin,
    )
    items = [FindingResponse.model_validate(f) for f in findings]
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=math.ceil(total / pagination.page_size) if pagination.page_size else 0,
    )


# ── Compteurs par statut ────────────────────────────────────────────
@router.get("/counts", response_model=FindingCountsByStatus)
def get_counts(
    assessment_id: int | None = Query(None),
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Compteurs de findings par statut."""
    counts = FindingService.counts_by_status(db, assessment_id=assessment_id)
    return FindingCountsByStatus(**counts)


# ── Détail d'un finding ─────────────────────────────────────────────
@router.get("/{finding_id}", response_model=FindingDetail)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Récupère le détail d'un finding avec historique."""
    finding = FindingService.get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding introuvable")
    return FindingDetail.model_validate(finding)


# ── Génération automatique ──────────────────────────────────────────
@router.post("/generate", response_model=FindingGenerateResponse, status_code=201)
def generate_findings(
    body: FindingGenerateRequest,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Génère des findings depuis les ControlResult non-conformes d'un assessment."""
    uid = rbac.user_id
    generated, skipped = FindingService.generate_from_assessment(db, body.assessment_id, user_id=uid)
    return FindingGenerateResponse(
        generated=generated,
        skipped=skipped,
        message=f"{generated} finding(s) créé(s), {skipped} ignoré(s) (déjà existants)",
    )


# ── Mise à jour du statut ───────────────────────────────────────────
@router.patch("/{finding_id}/status", response_model=FindingDetail)
def update_finding_status(
    finding_id: int,
    body: FindingStatusUpdate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Transition de statut d'un finding."""
    finding = FindingService.get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding introuvable")

    uid = rbac.user_id
    updated = FindingService.update_status(
        db,
        finding,
        new_status_str=body.status,
        user_id=uid,
        comment=body.comment,
        assigned_to=body.assigned_to,
    )

    return FindingDetail.model_validate(updated)


# ── Liaison doublon ─────────────────────────────────────────────────
@router.post("/{finding_id}/link-duplicate", response_model=FindingDetail)
def link_duplicate(
    finding_id: int,
    body: FindingLinkDuplicate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Lie un finding comme doublon d'un autre."""
    finding = FindingService.get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding introuvable")

    updated = FindingService.link_duplicate(db, finding, body.duplicate_of_id)

    return FindingDetail.model_validate(updated)
