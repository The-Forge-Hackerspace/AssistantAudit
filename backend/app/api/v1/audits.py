"""
Routes Audits : CRUD et gestion de statut.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, get_current_admin, PaginationParams
from ...core.helpers import get_or_404
from ...models.audit import Audit, AuditStatus
from ...models.entreprise import Entreprise
from ...models.user import User
from ...schemas.audit import AuditCreate, AuditRead, AuditDetail, AuditUpdate
from ...schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AuditRead])
def list_audits(
    pagination: PaginationParams = Depends(),
    entreprise_id: int = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les audits (paginé, filtrable par entreprise)"""
    query = db.query(Audit)
    if entreprise_id:
        query = query.filter(Audit.entreprise_id == entreprise_id)
    total = query.count()
    items = query.order_by(Audit.date_debut.desc()).offset(pagination.offset).limit(pagination.page_size).all()
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
    _: User = Depends(get_current_auditeur),
):
    """Crée un nouveau projet d'audit"""
    get_or_404(db, Entreprise, body.entreprise_id)
    audit = Audit(
        nom_projet=body.nom_projet,
        entreprise_id=body.entreprise_id,
        objectifs=body.objectifs,
        limites=body.limites,
        hypotheses=body.hypotheses,
        risques_initiaux=body.risques_initiaux,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


@router.get("/{audit_id}", response_model=AuditDetail)
def get_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    audit = get_or_404(db, Audit, audit_id)
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
    _: User = Depends(get_current_auditeur),
):
    audit = get_or_404(db, Audit, audit_id)

    update_data = body.model_dump(exclude_unset=True)
    if "status" in update_data:
        update_data["status"] = AuditStatus(update_data["status"])
    for field, value in update_data.items():
        setattr(audit, field, value)

    db.commit()
    db.refresh(audit)
    return audit


@router.delete("/{audit_id}", response_model=MessageResponse)
def delete_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    audit = get_or_404(db, Audit, audit_id)
    db.delete(audit)
    db.commit()
    return MessageResponse(message=f"Audit '{audit.nom_projet}' supprimé")
