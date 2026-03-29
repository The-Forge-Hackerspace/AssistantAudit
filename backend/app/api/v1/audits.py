"""
Routes Audits : CRUD et gestion de statut.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, get_current_admin, PaginationParams
from ...models.user import User
from ...schemas.audit import AuditCreate, AuditRead, AuditDetail, AuditUpdate
from ...schemas.common import PaginatedResponse, MessageResponse
from ...services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AuditRead])
def list_audits(
    pagination: PaginationParams = Depends(),
    entreprise_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les audits (paginé, filtrable par entreprise)"""
    owner_id = None if current_user.role == "admin" else current_user.id
    items, total = AuditService.list_audits(
        db,
        owner_id=owner_id,
        entreprise_id=entreprise_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("", response_model=AuditRead, status_code=status.HTTP_201_CREATED)
def create_audit(
    body: AuditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Crée un nouveau projet d'audit"""
    return AuditService.create_audit(db, body, owner_id=current_user.id)


@router.get("/{audit_id}", response_model=AuditDetail)
def get_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owner_id = None if current_user.role == "admin" else current_user.id
    audit = AuditService.get_audit(db, audit_id, owner_id=owner_id)
    return AuditDetail(
        id=audit.id,
        nom_projet=audit.nom_projet,
        entreprise_id=audit.entreprise_id,
        status=audit.status.value,
        date_debut=audit.date_debut,
        objectifs=audit.objectifs,
        limites=audit.limites,
        hypotheses=audit.hypotheses,
        risques_initiaux=audit.risques_initiaux,
        lettre_mission_path=audit.lettre_mission_path,
        contrat_path=audit.contrat_path,
        planning_path=audit.planning_path,
        total_campaigns=len(audit.campaigns) if audit.campaigns else 0,
        entreprise_nom=audit.entreprise.nom if audit.entreprise else None,
    )


@router.put("/{audit_id}", response_model=AuditRead)
def update_audit(
    audit_id: int,
    body: AuditUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    owner_id = None if current_user.role == "admin" else current_user.id
    return AuditService.update_audit(db, audit_id, body, owner_id=owner_id)


@router.delete("/{audit_id}", response_model=MessageResponse)
def delete_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    nom = AuditService.delete_audit(db, audit_id)
    return MessageResponse(message=f"Audit '{nom}' supprimé")
