"""
Tests pour le service de gestion des fichiers preuves chiffres (Step 10).

Couvre :
- Upload avec chiffrement enveloppe + creation Attachment
- Download nouveau fichier (dechiffrement)
- Download ancien fichier (lecture directe depuis file_path)
- Download par un autre user -> 404
- Delete fichier + base
- Upload sans ownership -> 404
- Mode dev (passthrough sans ENCRYPTION_KEY)
- Fichier volumineux (1 MB+)
- Routes API (POST upload, GET download, DELETE)
"""
import os
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.attachment import Attachment
from app.services.file_service import FileService
from tests.factories import (
    AuditFactory,
    AssessmentCampaignFactory,
    AssessmentFactory,
    ControlFactory,
    ControlResultFactory,
    EntrepriseFactory,
    EquipementFactory,
    FrameworkCategoryFactory,
    FrameworkFactory,
    SiteFactory,
    UserFactory,
)


# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_blobs_dir(tmp_path, monkeypatch):
    """Configure DATA_DIR vers un repertoire temporaire."""
    blobs = tmp_path / "blobs"
    blobs.mkdir()
    frameworks = tmp_path / "frameworks"
    frameworks.mkdir()

    from app.core.config import get_settings
    real_settings = get_settings()

    monkeypatch.setattr(real_settings, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(real_settings, "FRAMEWORKS_DIR", str(frameworks))
    return tmp_path


@pytest.fixture
def file_service(monkeypatch):
    """FileService en mode passthrough (pas de FILE_ENCRYPTION_KEY)."""
    from app.core.config import get_settings
    real_settings = get_settings()
    monkeypatch.setattr(real_settings, "FILE_ENCRYPTION_KEY", "")
    return FileService()


@pytest.fixture
def file_service_encrypted(monkeypatch):
    """FileService avec chiffrement actif."""
    test_kek = os.urandom(32).hex()
    from app.core.config import get_settings
    real_settings = get_settings()
    monkeypatch.setattr(real_settings, "FILE_ENCRYPTION_KEY", test_kek)
    return FileService()


@pytest.fixture
def full_chain(db_session: Session):
    """
    Cree la chaine complete : User -> Audit -> Campaign -> Assessment -> ControlResult.
    Retourne un dict avec tous les objets.
    """
    uid = str(uuid.uuid4())[:8]

    owner = UserFactory.create(
        db_session, username=f"owner_{uid}", email=f"owner_{uid}@test.local", role="auditeur"
    )
    other_user = UserFactory.create(
        db_session, username=f"other_{uid}", email=f"other_{uid}@test.local", role="auditeur"
    )
    entreprise = EntrepriseFactory.create(db_session, nom=f"Corp_{uid}")
    site = SiteFactory.create(db_session, nom="Site A", entreprise_id=entreprise.id)
    equipement = EquipementFactory.create(db_session, site_id=site.id, hostname=f"host-{uid}")
    framework = FrameworkFactory.create(db_session, ref_id=f"FW_{uid}", name=f"Framework {uid}")
    category = FrameworkCategoryFactory.create(db_session, framework_id=framework.id)
    control = ControlFactory.create(db_session, category_id=category.id, ref_id=f"CTL_{uid}")

    audit = AuditFactory.create(
        db_session, nom_projet=f"Audit {uid}", entreprise_id=entreprise.id, owner_id=owner.id
    )
    campaign = AssessmentCampaignFactory.create(db_session, audit_id=audit.id)
    assessment = AssessmentFactory.create(
        db_session, campaign_id=campaign.id, equipement_id=equipement.id, framework_id=framework.id
    )
    control_result = ControlResultFactory.create(
        db_session, assessment_id=assessment.id, control_id=control.id
    )

    return {
        "owner": owner,
        "other_user": other_user,
        "audit": audit,
        "control_result": control_result,
    }


# ────────────────────────────────────────────────────────────────────────
# Tests unitaires — FileService
# ────────────────────────────────────────────────────────────────────────


class TestFileServiceUpload:
    """Tests pour FileService.upload_file."""

    def test_upload_creates_attachment_and_file(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        content = b"Hello, this is test evidence."
        attachment = file_service.upload_file(
            db=db_session,
            content=content,
            filename="evidence.txt",
            content_type="text/plain",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        assert attachment.id is not None
        assert attachment.original_filename == "evidence.txt"
        assert attachment.file_size == len(content)
        assert attachment.mime_type == "text/plain"
        assert attachment.file_uuid is not None
        assert attachment.uploaded_by == str(full_chain["owner"].id)

        # Verifier fichier sur disque
        blob_path = tmp_blobs_dir / "blobs" / f"{attachment.file_uuid}.enc"
        assert blob_path.exists()

    def test_upload_no_ownership_returns_404(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        with pytest.raises(HTTPException) as exc_info:
            file_service.upload_file(
                db=db_session,
                content=b"data",
                filename="test.txt",
                content_type="text/plain",
                control_result_id=full_chain["control_result"].id,
                user_id=full_chain["other_user"].id,
            )
        assert exc_info.value.status_code == 404

    def test_upload_nonexistent_control_result_returns_404(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        with pytest.raises(HTTPException) as exc_info:
            file_service.upload_file(
                db=db_session,
                content=b"data",
                filename="test.txt",
                content_type="text/plain",
                control_result_id=99999,
                user_id=full_chain["owner"].id,
            )
        assert exc_info.value.status_code == 404

    def test_upload_with_description(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        attachment = file_service.upload_file(
            db=db_session,
            content=b"data",
            filename="config.yaml",
            content_type="application/x-yaml",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
            description="Configuration du pare-feu",
        )
        db_session.commit()
        assert attachment.description == "Configuration du pare-feu"


class TestFileServiceUploadEncrypted:
    """Tests avec chiffrement actif."""

    def test_upload_encrypted_stores_dek(
        self, db_session, full_chain, file_service_encrypted, tmp_blobs_dir
    ):
        content = b"Sensitive evidence data"
        attachment = file_service_encrypted.upload_file(
            db=db_session,
            content=content,
            filename="secret.pdf",
            content_type="application/pdf",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        assert attachment.encrypted_dek is not None
        assert len(attachment.encrypted_dek) > 0
        assert attachment.dek_nonce is not None
        assert len(attachment.dek_nonce) > 0
        assert attachment.kek_version == 1

        # Verifier que le fichier sur disque n'est PAS le contenu en clair
        blob_path = tmp_blobs_dir / "blobs" / f"{attachment.file_uuid}.enc"
        encrypted_on_disk = blob_path.read_bytes()
        assert encrypted_on_disk != content


class TestFileServiceDownload:
    """Tests pour FileService.download_file."""

    def test_download_new_file_passthrough(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        original_content = b"Evidence content for download test"
        attachment = file_service.upload_file(
            db=db_session,
            content=original_content,
            filename="report.pdf",
            content_type="application/pdf",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        content, filename, mime = file_service.download_file(
            db=db_session,
            attachment_id=attachment.id,
            user_id=full_chain["owner"].id,
        )
        assert content == original_content
        assert filename == "report.pdf"
        assert mime == "application/pdf"

    def test_download_encrypted_file_decrypts_correctly(
        self, db_session, full_chain, file_service_encrypted, tmp_blobs_dir
    ):
        original_content = b"Top secret evidence"
        attachment = file_service_encrypted.upload_file(
            db=db_session,
            content=original_content,
            filename="classified.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        content, filename, mime = file_service_encrypted.download_file(
            db=db_session,
            attachment_id=attachment.id,
            user_id=full_chain["owner"].id,
        )
        assert content == original_content
        assert filename == "classified.docx"

    def test_download_other_user_returns_404(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        attachment = file_service.upload_file(
            db=db_session,
            content=b"private data",
            filename="private.txt",
            content_type="text/plain",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            file_service.download_file(
                db=db_session,
                attachment_id=attachment.id,
                user_id=full_chain["other_user"].id,
            )
        assert exc_info.value.status_code == 404

    def test_download_legacy_file_without_dek(
        self, db_session, full_chain, tmp_blobs_dir, file_service
    ):
        """Test backward compat : fichier ancien sans encrypted_dek."""
        # Creer un fichier legacy directement
        # Le FRAMEWORKS_DIR est tmp_blobs_dir/frameworks, donc le data dir parent est tmp_blobs_dir
        from app.core.config import get_settings
        settings = get_settings()
        base_data = Path(settings.FRAMEWORKS_DIR).parent / "data"
        legacy_dir = base_data / "legacy"
        legacy_dir.mkdir(parents=True, exist_ok=True)

        legacy_content = b"Legacy unencrypted file content"
        legacy_file = legacy_dir / "old_file.txt"
        legacy_file.write_bytes(legacy_content)

        rel_path = "legacy/old_file.txt"

        # Creer l'attachment sans DEK (mode ancien)
        attachment = Attachment(
            control_result_id=full_chain["control_result"].id,
            original_filename="old_file.txt",
            stored_filename="old_file.txt",
            file_path=rel_path,
            mime_type="text/plain",
            file_size=len(legacy_content),
            uploaded_by="legacy_user",
            encrypted_dek=None,
            dek_nonce=None,
            kek_version=None,
        )
        db_session.add(attachment)
        db_session.commit()
        db_session.refresh(attachment)

        content, filename, mime = file_service.download_file(
            db=db_session,
            attachment_id=attachment.id,
            user_id=full_chain["owner"].id,
        )
        assert content == legacy_content
        assert filename == "old_file.txt"

    def test_download_nonexistent_attachment_returns_404(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        with pytest.raises(HTTPException) as exc_info:
            file_service.download_file(
                db=db_session,
                attachment_id=99999,
                user_id=full_chain["owner"].id,
            )
        assert exc_info.value.status_code == 404


class TestFileServiceDelete:
    """Tests pour FileService.delete_file."""

    def test_delete_removes_file_and_record(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        attachment = file_service.upload_file(
            db=db_session,
            content=b"to be deleted",
            filename="temp.txt",
            content_type="text/plain",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        file_uuid = attachment.file_uuid
        attachment_id = attachment.id
        blob_path = tmp_blobs_dir / "blobs" / f"{file_uuid}.enc"
        assert blob_path.exists()

        file_service.delete_file(
            db=db_session,
            attachment_id=attachment_id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        # Fichier supprime du disque
        assert not blob_path.exists()

        # Enregistrement supprime de la base
        assert db_session.get(Attachment, attachment_id) is None

    def test_delete_other_user_returns_404(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        attachment = file_service.upload_file(
            db=db_session,
            content=b"data",
            filename="test.txt",
            content_type="text/plain",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            file_service.delete_file(
                db=db_session,
                attachment_id=attachment.id,
                user_id=full_chain["other_user"].id,
            )
        assert exc_info.value.status_code == 404


class TestFileServiceLargeFile:
    """Test fichier volumineux."""

    def test_upload_download_1mb_file(
        self, db_session, full_chain, file_service, tmp_blobs_dir
    ):
        large_content = os.urandom(1024 * 1024)  # 1 MB
        attachment = file_service.upload_file(
            db=db_session,
            content=large_content,
            filename="big_scan.pcap",
            content_type="application/vnd.tcpdump.pcap",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        assert attachment.file_size == 1024 * 1024

        content, _, _ = file_service.download_file(
            db=db_session,
            attachment_id=attachment.id,
            user_id=full_chain["owner"].id,
        )
        assert content == large_content

    def test_upload_download_1mb_encrypted(
        self, db_session, full_chain, file_service_encrypted, tmp_blobs_dir
    ):
        large_content = os.urandom(1024 * 1024)  # 1 MB
        attachment = file_service_encrypted.upload_file(
            db=db_session,
            content=large_content,
            filename="big_encrypted.bin",
            content_type="application/octet-stream",
            control_result_id=full_chain["control_result"].id,
            user_id=full_chain["owner"].id,
        )
        db_session.commit()

        content, _, _ = file_service_encrypted.download_file(
            db=db_session,
            attachment_id=attachment.id,
            user_id=full_chain["owner"].id,
        )
        assert content == large_content


# ────────────────────────────────────────────────────────────────────────
# Tests API routes
# ────────────────────────────────────────────────────────────────────────


class TestFilesAPI:
    """Tests des routes /api/v1/files/."""

    def _make_chain(self, db_session, user):
        """Helper pour creer la chaine de donnees pour un user."""
        uid = str(uuid.uuid4())[:8]
        entreprise = EntrepriseFactory.create(db_session, nom=f"API Corp {uid}")
        site = SiteFactory.create(db_session, nom="API Site", entreprise_id=entreprise.id)
        equipement = EquipementFactory.create(db_session, site_id=site.id, hostname=f"api-host-{uid}")
        framework = FrameworkFactory.create(db_session, ref_id=f"API_FW_{uid}", name=f"API Framework {uid}")
        category = FrameworkCategoryFactory.create(db_session, framework_id=framework.id)
        control = ControlFactory.create(db_session, category_id=category.id, ref_id=f"API_CTL_{uid}")
        audit = AuditFactory.create(
            db_session, nom_projet=f"API Audit {uid}", entreprise_id=entreprise.id, owner_id=user.id
        )
        campaign = AssessmentCampaignFactory.create(db_session, audit_id=audit.id)
        assessment = AssessmentFactory.create(
            db_session, campaign_id=campaign.id, equipement_id=equipement.id, framework_id=framework.id
        )
        cr = ControlResultFactory.create(
            db_session, assessment_id=assessment.id, control_id=control.id
        )
        return cr

    def test_upload_endpoint(self, client, db_session, auditeur_user, tmp_blobs_dir, monkeypatch):
        cr = self._make_chain(db_session, auditeur_user)
        token = create_access_token(subject=auditeur_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        # Monkeypatch FILE_ENCRYPTION_KEY pour mode passthrough
        from app.core.config import get_settings
        monkeypatch.setattr(get_settings(), "FILE_ENCRYPTION_KEY", "")

        response = client.post(
            "/api/v1/files/upload",
            data={"control_result_id": str(cr.id)},
            files={"file": ("test.txt", BytesIO(b"data"), "text/plain")},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["original_filename"] == "test.txt"
        assert data["mime_type"] == "text/plain"
        assert data["file_size"] == 4

    def test_upload_forbidden_extension(self, client, db_session, auditeur_user):
        token = create_access_token(subject=auditeur_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/v1/files/upload",
            data={"control_result_id": "1"},
            files={"file": ("malware.exe", BytesIO(b"bad"), "application/octet-stream")},
            headers=headers,
        )
        assert response.status_code == 400
        assert "non autorisee" in response.json()["detail"]

    def test_download_endpoint(self, client, db_session, auditeur_user):
        token = create_access_token(subject=auditeur_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.files._file_service") as mock_svc:
            mock_svc.download_file.return_value = (b"file content", "report.pdf", "application/pdf")

            response = client.get(
                "/api/v1/files/download/1",
                headers=headers,
            )
            assert response.status_code == 200
            assert response.content == b"file content"
            assert "report.pdf" in response.headers.get("content-disposition", "")

    def test_delete_endpoint(self, client, db_session, auditeur_user):
        token = create_access_token(subject=auditeur_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.files._file_service") as mock_svc:
            mock_svc.delete_file.return_value = None

            response = client.delete(
                "/api/v1/files/1",
                headers=headers,
            )
            assert response.status_code == 204

    def test_upload_unauthenticated(self, client):
        response = client.post(
            "/api/v1/files/upload",
            data={"control_result_id": "1"},
            files={"file": ("test.txt", BytesIO(b"data"), "text/plain")},
        )
        assert response.status_code == 401

    def test_download_unauthenticated(self, client):
        response = client.get("/api/v1/files/download/1")
        assert response.status_code == 401

    def test_delete_lecteur_forbidden(self, client, db_session, lecteur_user):
        token = create_access_token(subject=lecteur_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete(
            "/api/v1/files/1",
            headers=headers,
        )
        assert response.status_code == 403
