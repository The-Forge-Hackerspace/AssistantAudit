"""
Service Audit : CRUD pour les projets d'audit.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.audit_logger import log_access_denied
from ..core.helpers import get_or_404
from ..models.audit import Audit, AuditStatus
from ..models.entreprise import Entreprise
from ..schemas.audit import AuditCreate, AuditUpdate


class AuditService:
    @staticmethod
    def list_audits(
        db: Session,
        owner_id: int | None = None,
        entreprise_id: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Audit], int]:
        """Liste les audits avec pagination et filtres optionnels."""
        query = db.query(Audit)
        if owner_id is not None:
            query = query.filter(Audit.owner_id == owner_id)
        if entreprise_id is not None:
            query = query.filter(Audit.entreprise_id == entreprise_id)
        total = query.count()
        items = query.order_by(Audit.date_debut.desc()).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def get_audit(db: Session, audit_id: int, owner_id: int | None = None) -> Audit:
        """Recupere un audit par ID. Si owner_id fourni, verifie l'appartenance."""
        audit = get_or_404(db, Audit, audit_id)
        if owner_id is not None and audit.owner_id != owner_id:
            log_access_denied(owner_id, "Audit", audit_id)
            raise HTTPException(status_code=404, detail="Audit introuvable")
        return audit

    @staticmethod
    def create_audit(db: Session, data: AuditCreate, owner_id: int) -> Audit:
        """Cree un nouveau projet d'audit."""
        get_or_404(db, Entreprise, data.entreprise_id)
        audit = Audit(
            nom_projet=data.nom_projet,
            entreprise_id=data.entreprise_id,
            objectifs=data.objectifs,
            limites=data.limites,
            hypotheses=data.hypotheses,
            risques_initiaux=data.risques_initiaux,
            owner_id=owner_id,
            date_fin=data.date_fin,
            client_contact_name=data.client_contact_name,
            client_contact_title=data.client_contact_title,
            client_contact_email=data.client_contact_email,
            client_contact_phone=data.client_contact_phone,
            access_level=data.access_level,
            access_missing_details=data.access_missing_details,
            intervention_window=data.intervention_window,
            intervention_constraints=data.intervention_constraints,
            scope_covered=data.scope_covered,
            scope_excluded=data.scope_excluded,
            audit_type=data.audit_type,
        )
        db.add(audit)
        db.flush()
        db.refresh(audit)
        return audit

    @staticmethod
    def update_audit(
        db: Session,
        audit_id: int,
        data: AuditUpdate,
        owner_id: int | None = None,
    ) -> Audit:
        """Met a jour un audit existant."""
        audit = get_or_404(db, Audit, audit_id)
        if owner_id is not None and audit.owner_id != owner_id:
            log_access_denied(owner_id, "Audit", audit_id, action="update")
            raise HTTPException(status_code=404, detail="Audit introuvable")

        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data:
            update_data["status"] = AuditStatus(update_data["status"])
        for field, value in update_data.items():
            setattr(audit, field, value)

        db.flush()
        db.refresh(audit)
        return audit

    @staticmethod
    def delete_audit(db: Session, audit_id: int, owner_id: int | None = None) -> str:
        """Supprime un audit. Retourne le nom du projet supprime."""
        audit = get_or_404(db, Audit, audit_id)
        if owner_id is not None and audit.owner_id != owner_id:
            log_access_denied(owner_id, "Audit", audit_id, action="delete")
            raise HTTPException(status_code=404, detail="Audit introuvable")
        nom = audit.nom_projet
        db.delete(audit)
        db.flush()
        return nom
