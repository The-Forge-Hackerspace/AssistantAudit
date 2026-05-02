"""
Tests RBAC — isolation de list_attachments par ownership.

Vérifie que list_attachments filtre via la chaîne FK :
Attachment → ControlResult → Assessment → Campaign → Audit → owner_id.
"""

import uuid

from app.models.attachment import Attachment
from tests.factories import (
    AssessmentCampaignFactory,
    AssessmentFactory,
    AuditFactory,
    ControlFactory,
    ControlResultFactory,
    EntrepriseFactory,
    EquipementFactory,
    FrameworkCategoryFactory,
    FrameworkFactory,
    SiteFactory,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _create_attachment_chain(db, owner, *, uid=None):
    """Crée la chaîne complète jusqu'à un Attachment pour un owner donné."""
    uid = uid or str(uuid.uuid4())[:8]
    ent = EntrepriseFactory.create(db, nom=f"Ent_{uid}")
    site = SiteFactory.create(db, nom=f"Site_{uid}", entreprise_id=ent.id)
    equip = EquipementFactory.create(db, site_id=site.id, hostname=f"host-{uid}")
    fw = FrameworkFactory.create(db, ref_id=f"FW_{uid}", name=f"FW {uid}")
    cat = FrameworkCategoryFactory.create(db, framework_id=fw.id)
    ctrl = ControlFactory.create(db, category_id=cat.id, ref_id=f"CTL_{uid}")

    audit = AuditFactory.create(
        db,
        nom_projet=f"Audit {uid}",
        entreprise_id=ent.id,
        owner_id=owner.id,
    )
    campaign = AssessmentCampaignFactory.create(db, audit_id=audit.id)
    assessment = AssessmentFactory.create(
        db,
        campaign_id=campaign.id,
        equipement_id=equip.id,
        framework_id=fw.id,
    )
    cr = ControlResultFactory.create(db, assessment_id=assessment.id, control_id=ctrl.id)

    att = Attachment(
        control_result_id=cr.id,
        original_filename="test.png",
        stored_filename=f"{uid}_test.png",
        file_path=f"{uid}/test.png",
        mime_type="image/png",
        file_size=100,
        uploaded_by=owner.username,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    db.refresh(cr)
    return cr, att


# ══════════════════════════════════════════════════════════════════════
# list_attachments — GET /attachments/control-result/{result_id}
# ══════════════════════════════════════════════════════════════════════


class TestListAttachmentsIsolation:
    def test_owner_sees_own_attachments(
        self,
        client,
        db_session,
        auditeur_user,
        auditeur_headers,
    ):
        """Non-régression : un auditeur voit ses propres pièces jointes."""
        cr, att = _create_attachment_chain(db_session, auditeur_user)
        r = client.get(
            f"/api/v1/attachments/control-result/{cr.id}",
            headers=auditeur_headers,
        )
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()]
        assert att.id in ids

    def test_other_user_sees_empty_list(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """Auditeur B ne voit pas les attachments d'auditeur A (liste vide)."""
        cr, _ = _create_attachment_chain(db_session, auditeur_user)
        r = client.get(
            f"/api/v1/attachments/control-result/{cr.id}",
            headers=second_auditeur_headers,
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_admin_sees_all_attachments(
        self,
        client,
        db_session,
        auditeur_user,
        admin_headers,
    ):
        """L'admin voit les attachments de n'importe quel auditeur."""
        cr, att = _create_attachment_chain(db_session, auditeur_user)
        r = client.get(
            f"/api/v1/attachments/control-result/{cr.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()]
        assert att.id in ids


# ═════════════════════════════════════════════════════════════════════
# upload_attachment — POST /attachments/control-result/{result_id}/upload (BOLA fix S-001 — TOS-74)
# ═════════════════════════════════════════════════════════════════════


def _build_control_result_chain(db, owner, *, uid=None):
    """Crée la chaîne jusqu'au ControlResult (sans Attachment) pour les tests d'upload."""
    uid = uid or str(uuid.uuid4())[:8]
    ent = EntrepriseFactory.create(db, nom=f"Ent_{uid}")
    site = SiteFactory.create(db, nom=f"Site_{uid}", entreprise_id=ent.id)
    equip = EquipementFactory.create(db, site_id=site.id, hostname=f"host-{uid}")
    fw = FrameworkFactory.create(db, ref_id=f"FW_{uid}", name=f"FW {uid}")
    cat = FrameworkCategoryFactory.create(db, framework_id=fw.id)
    ctrl = ControlFactory.create(db, category_id=cat.id, ref_id=f"CTL_{uid}")

    audit = AuditFactory.create(
        db,
        nom_projet=f"Audit {uid}",
        entreprise_id=ent.id,
        owner_id=owner.id,
    )
    campaign = AssessmentCampaignFactory.create(db, audit_id=audit.id)
    assessment = AssessmentFactory.create(
        db,
        campaign_id=campaign.id,
        equipement_id=equip.id,
        framework_id=fw.id,
    )
    cr = ControlResultFactory.create(db, assessment_id=assessment.id, control_id=ctrl.id)
    return cr


class TestUploadAttachmentBolaIsolation:
    """BOLA fix TOS-74 : la route legacy vérifie l'ownership avant toute IO."""

    def test_owner_can_upload(
        self,
        client,
        db_session,
        auditeur_user,
        auditeur_headers,
    ):
        """Non-régression : l'owner peut uploader sur son propre control_result."""
        cr = _build_control_result_chain(db_session, auditeur_user)

        # auditeur_headers contient Content-Type: application/json — incompatible multipart.
        token_only = {"Authorization": auditeur_headers["Authorization"]}
        files = {"file": ("shot.png", b"\x89PNG\r\n\x1a\n_test", "image/png")}
        r = client.post(
            f"/api/v1/attachments/control-result/{cr.id}/upload",
            headers=token_only,
            files=files,
        )

        assert r.status_code == 201, r.text
        body = r.json()
        assert body["control_result_id"] == cr.id
        assert body["original_filename"] == "shot.png"
        assert (
            db_session.query(Attachment)
            .filter(Attachment.control_result_id == cr.id)
            .count()
            == 1
        )

    def test_non_owner_gets_404_and_no_disk_write(
        self,
        client,
        db_session,
        auditeur_user,
        second_auditeur_headers,
    ):
        """BOLA : auditeur-B upload sur audit owner=auditeur-A → 404 générique, aucun fichier disque, aucun row Attachment."""
        cr = _build_control_result_chain(db_session, auditeur_user)

        token_only = {"Authorization": second_auditeur_headers["Authorization"]}
        files = {"file": ("evil.png", b"\x89PNG\r\n\x1a\n_evil", "image/png")}
        r = client.post(
            f"/api/v1/attachments/control-result/{cr.id}/upload",
            headers=token_only,
            files=files,
        )

        assert r.status_code == 404, r.text
        # Message générique — pas de leak d'existence
        assert "introuvable" in r.json().get("detail", "").lower()
        # Aucun row Attachment créé
        assert (
            db_session.query(Attachment)
            .filter(Attachment.control_result_id == cr.id)
            .count()
            == 0
        )

    def test_admin_can_upload_on_other_user_audit(
        self,
        client,
        db_session,
        auditeur_user,
        admin_headers,
    ):
        """Admin-aware : admin peut uploader sur un audit d'un autre user (AC3)."""
        cr = _build_control_result_chain(db_session, auditeur_user)

        token_only = {"Authorization": admin_headers["Authorization"]}
        files = {"file": ("adm.png", b"\x89PNG\r\n\x1a\n_admin", "image/png")}
        r = client.post(
            f"/api/v1/attachments/control-result/{cr.id}/upload",
            headers=token_only,
            files=files,
        )

        assert r.status_code == 201, r.text
        body = r.json()
        assert body["control_result_id"] == cr.id

    def test_missing_result_id_returns_404_no_disk(
        self,
        client,
        db_session,
        auditeur_headers,
    ):
        """AC4 : result_id inexistant → 404 + aucun fichier disque."""
        token_only = {"Authorization": auditeur_headers["Authorization"]}
        files = {"file": ("ghost.png", b"\x89PNG\r\n\x1a\n_ghost", "image/png")}
        r = client.post(
            "/api/v1/attachments/control-result/999999/upload",
            headers=token_only,
            files=files,
        )

        assert r.status_code == 404, r.text
        # Aucun row Attachment
        assert db_session.query(Attachment).count() == 0

