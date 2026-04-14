"""Service checklists — instanciation, réponses, progression."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from ..models.audit import Audit
from ..models.checklist import (
    ChecklistInstance,
    ChecklistItem,
    ChecklistResponse,
    ChecklistSection,
    ChecklistTemplate,
)
from ..schemas.checklist import ChecklistInstanceCreate, ChecklistResponseUpdate


class ChecklistService:
    @staticmethod
    def _check_audit_access(db: Session, audit_id: int, user_id: int, is_admin: bool) -> Audit:
        """Vérifie que l'utilisateur a accès à l'audit. 404 si non trouvé."""
        query = db.query(Audit).filter(Audit.id == audit_id)
        if not is_admin:
            query = query.filter(Audit.owner_id == user_id)
        audit = query.first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit non trouvé")
        return audit

    @staticmethod
    def list_templates(db: Session, category: str | None = None) -> list[ChecklistTemplate]:
        """Liste les templates disponibles."""
        query = db.query(ChecklistTemplate)
        if category:
            query = query.filter(ChecklistTemplate.category == category)
        return query.order_by(ChecklistTemplate.name).all()

    @staticmethod
    def get_template(db: Session, template_id: int) -> ChecklistTemplate:
        """Récupère un template avec ses sections et items."""
        tpl = (
            db.query(ChecklistTemplate)
            .options(joinedload(ChecklistTemplate.sections).joinedload(ChecklistSection.items))
            .filter(ChecklistTemplate.id == template_id)
            .first()
        )
        if not tpl:
            raise HTTPException(status_code=404, detail="Template non trouvé")
        return tpl

    @staticmethod
    def create_instance(db: Session, data: ChecklistInstanceCreate, user_id: int, is_admin: bool) -> ChecklistInstance:
        """Instancie une checklist pour un audit."""
        # Vérifier accès audit
        ChecklistService._check_audit_access(db, data.audit_id, user_id, is_admin)

        # Vérifier que le template existe
        tpl = db.query(ChecklistTemplate).filter(ChecklistTemplate.id == data.template_id).first()
        if not tpl:
            raise HTTPException(status_code=404, detail="Template non trouvé")

        # Vérifier unicité
        existing = (
            db.query(ChecklistInstance)
            .filter(
                ChecklistInstance.template_id == data.template_id,
                ChecklistInstance.audit_id == data.audit_id,
                ChecklistInstance.site_id == data.site_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Cette checklist existe déjà pour cet audit")

        instance = ChecklistInstance(
            template_id=data.template_id,
            audit_id=data.audit_id,
            site_id=data.site_id,
            filled_by=user_id,
            status="draft",
        )
        db.add(instance)
        db.flush()
        db.refresh(instance)
        return instance

    @staticmethod
    def get_instance(db: Session, instance_id: int, user_id: int, is_admin: bool) -> ChecklistInstance:
        """Récupère une instance avec ses réponses."""
        instance = (
            db.query(ChecklistInstance)
            .options(joinedload(ChecklistInstance.responses))
            .filter(ChecklistInstance.id == instance_id)
            .first()
        )
        if not instance:
            raise HTTPException(status_code=404, detail="Instance non trouvée")
        # Vérifier accès via l'audit
        ChecklistService._check_audit_access(db, instance.audit_id, user_id, is_admin)
        return instance

    @staticmethod
    def list_instances(db: Session, audit_id: int, user_id: int, is_admin: bool) -> list[ChecklistInstance]:
        """Liste les instances de checklist pour un audit."""
        ChecklistService._check_audit_access(db, audit_id, user_id, is_admin)
        return db.query(ChecklistInstance).filter(ChecklistInstance.audit_id == audit_id).all()

    @staticmethod
    def respond_to_item(
        db: Session, instance_id: int, item_id: int, data: ChecklistResponseUpdate, user_id: int, is_admin: bool
    ) -> ChecklistResponse:
        """Répond à un item (upsert : crée ou met à jour)."""
        instance = ChecklistService.get_instance(db, instance_id, user_id, is_admin)

        # Vérifier que l'item appartient au template de l'instance
        item = (
            db.query(ChecklistItem)
            .join(ChecklistSection)
            .filter(
                ChecklistItem.id == item_id,
                ChecklistSection.template_id == instance.template_id,
            )
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item non trouvé dans ce template")

        # Upsert
        response = (
            db.query(ChecklistResponse)
            .filter(
                ChecklistResponse.instance_id == instance_id,
                ChecklistResponse.item_id == item_id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if response:
            response.status = data.status
            response.note = data.note
            response.responded_by = user_id
            response.responded_at = now
        else:
            response = ChecklistResponse(
                instance_id=instance_id,
                item_id=item_id,
                status=data.status,
                note=data.note,
                responded_by=user_id,
                responded_at=now,
            )
            db.add(response)

        # Mettre à jour le statut de l'instance si nécessaire
        if instance.status == "draft":
            instance.status = "in_progress"
            instance.started_at = now

        db.flush()
        db.refresh(response)
        return response

    @staticmethod
    def get_progress(db: Session, instance_id: int) -> dict:
        """Calcule la progression d'une instance."""
        instance = db.query(ChecklistInstance).filter(ChecklistInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="Instance non trouvée")

        # Compter les items du template
        total_items = (
            db.query(ChecklistItem)
            .join(ChecklistSection)
            .filter(ChecklistSection.template_id == instance.template_id)
            .count()
        )

        # Compter les réponses
        responses = db.query(ChecklistResponse).filter(ChecklistResponse.instance_id == instance_id).all()

        answered = len([r for r in responses if r.status != "UNCHECKED"])
        ok_count = len([r for r in responses if r.status == "OK"])
        nok_count = len([r for r in responses if r.status == "NOK"])
        na_count = len([r for r in responses if r.status == "NA"])

        return {
            "total_items": total_items,
            "answered": answered,
            "ok": ok_count,
            "nok": nok_count,
            "na": na_count,
            "unchecked": total_items - answered,
            "progress_percent": round(answered / total_items * 100) if total_items > 0 else 0,
        }

    @staticmethod
    def complete_instance(db: Session, instance_id: int, user_id: int, is_admin: bool) -> ChecklistInstance:
        """Marque une instance comme complétée."""
        instance = ChecklistService.get_instance(db, instance_id, user_id, is_admin)
        instance.status = "completed"
        instance.completed_at = datetime.now(timezone.utc)
        db.flush()
        db.refresh(instance)
        return instance

    @staticmethod
    def delete_instance(db: Session, instance_id: int, user_id: int, is_admin: bool) -> str:
        """Supprime une instance et ses réponses."""
        instance = ChecklistService.get_instance(db, instance_id, user_id, is_admin)
        db.delete(instance)
        db.flush()
        return f"Instance {instance_id} supprimée"
