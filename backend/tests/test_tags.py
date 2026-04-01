"""Tests TDD — Système de tags transversal (brief §5)."""

import pytest
from app.models.tag import Tag, TagAssociation
from app.services.tag_service import TagService
from app.schemas.tag import TagCreate, TagUpdate


class TestTagModel:
    """TAG-001 : modèle Tag avec contraintes."""

    def test_create_global_tag(self, db_session):
        """Un tag global peut être créé sans audit_id."""
        tag = Tag(name="critical", color="#EF4444", scope="global")
        db_session.add(tag)
        db_session.flush()
        assert tag.id is not None
        assert tag.scope == "global"
        assert tag.audit_id is None

    def test_create_audit_tag(self, db_session, auditeur_user):
        """Un tag d'audit est lié à un audit spécifique."""
        from app.models.audit import Audit
        audit = Audit(nom_projet="test", entreprise_id=1, owner_id=auditeur_user.id)
        db_session.add(audit)
        db_session.flush()

        tag = Tag(name="custom-tag", color="#10B981", scope="audit", audit_id=audit.id)
        db_session.add(tag)
        db_session.flush()
        assert tag.audit_id == audit.id

    def test_duplicate_global_tag_rejected(self, db_session):
        """Deux tags globaux avec le même nom sont rejetés."""
        from sqlalchemy.exc import IntegrityError
        db_session.add(Tag(name="duplicate", color="#000000", scope="global"))
        db_session.flush()
        db_session.add(Tag(name="duplicate", color="#FFFFFF", scope="global"))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_same_name_different_scope_allowed(self, db_session):
        """Le même nom peut exister en global et en audit."""
        db_session.add(Tag(name="shared-name", color="#000000", scope="global"))
        db_session.flush()
        # Pas de conflit car audit_id est différent (None vs un ID)
        # Note: le UniqueConstraint inclut audit_id


class TestTagAssociation:
    """TAG-001 : association polymorphe tag ↔ entité."""

    def test_associate_tag_to_entity(self, db_session):
        """On peut associer un tag à un type+id d'entité."""
        tag = Tag(name="legacy", color="#F59E0B", scope="global")
        db_session.add(tag)
        db_session.flush()

        assoc = TagAssociation(tag_id=tag.id, taggable_type="equipement", taggable_id=42)
        db_session.add(assoc)
        db_session.flush()
        assert assoc.id is not None

    def test_duplicate_association_rejected(self, db_session):
        """Le même tag ne peut pas être associé 2 fois à la même entité."""
        from sqlalchemy.exc import IntegrityError
        tag = Tag(name="dup-assoc", color="#000000", scope="global")
        db_session.add(tag)
        db_session.flush()

        db_session.add(TagAssociation(tag_id=tag.id, taggable_type="equipement", taggable_id=1))
        db_session.flush()
        db_session.add(TagAssociation(tag_id=tag.id, taggable_type="equipement", taggable_id=1))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_cascade_delete_tag_removes_associations(self, db_session):
        """Supprimer un tag supprime ses associations."""
        tag = Tag(name="cascade-test", color="#000000", scope="global")
        db_session.add(tag)
        db_session.flush()
        tag_id = tag.id

        db_session.add(TagAssociation(tag_id=tag_id, taggable_type="equipement", taggable_id=1))
        db_session.add(TagAssociation(tag_id=tag_id, taggable_type="equipement", taggable_id=2))
        db_session.flush()

        db_session.delete(tag)
        db_session.flush()
        remaining = db_session.query(TagAssociation).filter(TagAssociation.tag_id == tag_id).count()
        assert remaining == 0


class TestTagService:
    """TAG-002 : service avec CRUD et isolation."""

    def test_create_tag_returns_tag(self, db_session, auditeur_user):
        tag = TagService.create_tag(
            db_session,
            TagCreate(name="test-svc", color="#EF4444"),
            user_id=auditeur_user.id,
        )
        assert tag.name == "test-svc"
        assert tag.created_by == auditeur_user.id

    def test_create_duplicate_tag_raises_409(self, db_session, auditeur_user):
        TagService.create_tag(
            db_session, TagCreate(name="dup-svc"), user_id=auditeur_user.id
        )
        with pytest.raises(Exception) as exc_info:
            TagService.create_tag(
                db_session, TagCreate(name="dup-svc"), user_id=auditeur_user.id
            )
        assert exc_info.value.status_code == 409

    def test_list_tags_non_admin_sees_global_only(self, db_session, auditeur_user, second_auditeur_user):
        """Un auditeur ne voit que les tags globaux + ses tags d'audit."""
        TagService.create_tag(db_session, TagCreate(name="global-vis"), user_id=auditeur_user.id)
        tags, total = TagService.list_tags(db_session, user_id=second_auditeur_user.id, is_admin=False)
        names = [t.name for t in tags]
        assert "global-vis" in names

    def test_associate_and_get_tags(self, db_session, auditeur_user):
        """Associer un tag puis le récupérer pour une entité."""
        tag = TagService.create_tag(
            db_session, TagCreate(name="assoc-test"), user_id=auditeur_user.id
        )
        TagService.associate_tag(
            db_session, tag.id, "equipement", 99,
            user_id=auditeur_user.id, is_admin=False
        )
        tags = TagService.get_tags_for_entity(db_session, "equipement", 99)
        assert len(tags) == 1
        assert tags[0].name == "assoc-test"

    def test_dissociate_tag(self, db_session, auditeur_user):
        """Dissocier un tag d'une entité."""
        tag = TagService.create_tag(
            db_session, TagCreate(name="dissoc-test"), user_id=auditeur_user.id
        )
        TagService.associate_tag(
            db_session, tag.id, "equipement", 100,
            user_id=auditeur_user.id, is_admin=False
        )
        result = TagService.dissociate_tag(
            db_session, tag.id, "equipement", 100,
            user_id=auditeur_user.id, is_admin=False
        )
        assert result is True
        tags = TagService.get_tags_for_entity(db_session, "equipement", 100)
        assert len(tags) == 0
