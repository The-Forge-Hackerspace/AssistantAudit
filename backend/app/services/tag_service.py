"""Service tags — CRUD, association, filtrage."""

from sqlalchemy.orm import Session

from ..core.errors import ConflictError, NotFoundError
from ..models.audit import Audit
from ..models.tag import Tag, TagAssociation
from ..schemas.tag import TagCreate, TagUpdate


class TagService:
    @staticmethod
    def list_tags(
        db: Session,
        user_id: int,
        is_admin: bool,
        audit_id: int | None = None,
        scope: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Tag], int]:
        """Liste les tags visibles par l'utilisateur."""
        query = db.query(Tag)

        if scope:
            query = query.filter(Tag.scope == scope)

        if audit_id:
            # Tags globaux + tags de cet audit (si l'utilisateur y a accès)
            if not is_admin:
                audit = db.query(Audit).filter(Audit.id == audit_id, Audit.owner_id == user_id).first()
                if not audit:
                    raise NotFoundError("Audit non trouvé")
            query = query.filter((Tag.scope == "global") | (Tag.audit_id == audit_id))
        elif not is_admin:
            # Sans audit_id : tags globaux + tags des audits de l'utilisateur
            user_audit_ids = db.query(Audit.id).filter(Audit.owner_id == user_id).scalar_subquery()
            query = query.filter((Tag.scope == "global") | (Tag.audit_id.in_(user_audit_ids)))

        total = query.count()
        tags = query.order_by(Tag.name).offset(offset).limit(limit).all()
        return tags, total

    @staticmethod
    def get_tag(db: Session, tag_id: int, user_id: int, is_admin: bool) -> Tag:
        """Récupère un tag par ID."""
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise NotFoundError("Tag non trouvé")
        # Vérifier l'accès pour les tags d'audit
        if tag.scope == "audit" and not is_admin:
            audit = db.query(Audit).filter(Audit.id == tag.audit_id, Audit.owner_id == user_id).first()
            if not audit:
                raise NotFoundError("Tag non trouvé")
        return tag

    @staticmethod
    def create_tag(db: Session, data: TagCreate, user_id: int, is_admin: bool = False) -> Tag:
        """Crée un tag. Vérifie l'accès à l'audit si scope='audit'."""
        # RBAC : vérifier que l'utilisateur a accès à l'audit référencé
        if data.scope == "audit" and data.audit_id is not None and not is_admin:
            audit = db.query(Audit).filter(Audit.id == data.audit_id, Audit.owner_id == user_id).first()
            if not audit:
                raise NotFoundError("Audit non trouvé")

        # Vérifier unicité
        existing = (
            db.query(Tag)
            .filter(
                Tag.name == data.name,
                Tag.scope == data.scope,
                Tag.audit_id == data.audit_id,
            )
            .first()
        )
        if existing:
            raise ConflictError("Tag déjà existant")

        tag = Tag(
            name=data.name,
            color=data.color,
            scope=data.scope,
            audit_id=data.audit_id,
            created_by=user_id,
        )
        db.add(tag)
        db.flush()
        db.refresh(tag)
        return tag

    @staticmethod
    def update_tag(db: Session, tag_id: int, data: TagUpdate, user_id: int, is_admin: bool) -> Tag:
        """Met à jour un tag."""
        tag = TagService.get_tag(db, tag_id, user_id, is_admin)
        updates = data.model_dump(exclude_unset=True)
        for key, val in updates.items():
            setattr(tag, key, val)
        db.flush()
        db.refresh(tag)
        return tag

    @staticmethod
    def delete_tag(db: Session, tag_id: int, user_id: int, is_admin: bool) -> str:
        """Supprime un tag. Les associations sont supprimées en cascade."""
        tag = TagService.get_tag(db, tag_id, user_id, is_admin)
        name = tag.name
        db.delete(tag)
        db.flush()
        return name

    @staticmethod
    def associate_tag(
        db: Session, tag_id: int, taggable_type: str, taggable_id: int, user_id: int, is_admin: bool
    ) -> TagAssociation:
        """Associe un tag à une entité."""
        # Vérifier que le tag existe et est accessible
        TagService.get_tag(db, tag_id, user_id, is_admin)

        # Vérifier qu'il n'y a pas déjà cette association
        existing = (
            db.query(TagAssociation)
            .filter(
                TagAssociation.tag_id == tag_id,
                TagAssociation.taggable_type == taggable_type,
                TagAssociation.taggable_id == taggable_id,
            )
            .first()
        )
        if existing:
            return existing  # Idempotent

        assoc = TagAssociation(
            tag_id=tag_id,
            taggable_type=taggable_type,
            taggable_id=taggable_id,
        )
        db.add(assoc)
        db.flush()
        db.refresh(assoc)
        return assoc

    @staticmethod
    def dissociate_tag(
        db: Session, tag_id: int, taggable_type: str, taggable_id: int, user_id: int, is_admin: bool
    ) -> bool:
        """Retire un tag d'une entité."""
        TagService.get_tag(db, tag_id, user_id, is_admin)
        assoc = (
            db.query(TagAssociation)
            .filter(
                TagAssociation.tag_id == tag_id,
                TagAssociation.taggable_type == taggable_type,
                TagAssociation.taggable_id == taggable_id,
            )
            .first()
        )
        if assoc:
            db.delete(assoc)
            db.flush()
            return True
        return False

    @staticmethod
    def get_tags_for_entity(db: Session, taggable_type: str, taggable_id: int) -> list[Tag]:
        """Récupère tous les tags d'une entité."""
        return (
            db.query(Tag)
            .join(TagAssociation)
            .filter(
                TagAssociation.taggable_type == taggable_type,
                TagAssociation.taggable_id == taggable_id,
            )
            .all()
        )
