"""
Service de gestion des fichiers preuves avec chiffrement enveloppe.

Gere deux modes :
- Nouveaux fichiers : chiffres avec EnvelopeEncryption, stockes dans data/blobs/{uuid}.enc
- Anciens fichiers (pre-migration) : non chiffres, stockes a file_path

Le service verifie systematiquement l'ownership via la chaine :
  Attachment -> ControlResult -> Assessment -> Campaign -> Audit -> owner_id
"""

import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.file_encryption import EnvelopeEncryption
from app.models.assessment import Assessment, AssessmentCampaign, ControlResult
from app.models.attachment import Attachment
from app.models.audit import Audit
from app.models.equipement import Equipement
from app.models.site import Site
from app.models.user import User

from ..core.errors import NotFoundError

logger = logging.getLogger(__name__)


def _get_blobs_dir() -> Path:
    """Retourne le repertoire des blobs, le cree si inexistant."""
    settings = get_settings()
    blobs_dir = Path(settings.DATA_DIR) / "blobs"
    blobs_dir.mkdir(parents=True, exist_ok=True)
    return blobs_dir


class FileService:
    """Service de gestion des fichiers preuves avec chiffrement enveloppe."""

    def __init__(self) -> None:
        self.envelope = EnvelopeEncryption()

    def _verify_control_result_ownership(self, db: Session, control_result_id: int, user_id: int) -> ControlResult:
        """
        Verifie que le control_result appartient au user via la chaine :
        ControlResult -> Assessment -> Campaign -> Audit -> owner_id.
        Retourne le ControlResult ou leve 404.
        """
        cr = (
            db.query(ControlResult)
            .join(Assessment, ControlResult.assessment_id == Assessment.id)
            .join(AssessmentCampaign, Assessment.campaign_id == AssessmentCampaign.id)
            .join(Audit, AssessmentCampaign.audit_id == Audit.id)
            .filter(
                ControlResult.id == control_result_id,
                Audit.owner_id == user_id,
            )
            .first()
        )
        if cr is None:
            raise NotFoundError("Ressource introuvable")
        return cr

    def _get_attachment_with_ownership(self, db: Session, attachment_id: int, user_id: int) -> Attachment:
        """
        Recupere un Attachment avec verification d'ownership via la chaine complete.
        Retourne 404 (pas 403) si non trouve ou pas au bon user.
        """
        attachment = (
            db.query(Attachment)
            .join(ControlResult, Attachment.control_result_id == ControlResult.id)
            .join(Assessment, ControlResult.assessment_id == Assessment.id)
            .join(AssessmentCampaign, Assessment.campaign_id == AssessmentCampaign.id)
            .join(Audit, AssessmentCampaign.audit_id == Audit.id)
            .filter(
                Attachment.id == attachment_id,
                Audit.owner_id == user_id,
            )
            .first()
        )
        if attachment is None:
            raise NotFoundError("Fichier introuvable")
        return attachment

    def upload_file(
        self,
        db: Session,
        content: bytes,
        filename: str,
        content_type: str,
        control_result_id: int,
        user_id: int,
        description: str | None = None,
    ) -> Attachment:
        """
        Chiffre et stocke un fichier preuve.

        Args:
            content: Contenu brut du fichier
            filename: Nom original du fichier
            content_type: Type MIME
            control_result_id: FK vers le resultat de controle
            user_id: ID de l'utilisateur courant (verification ownership)
            description: Description optionnelle

        Returns:
            Attachment cree en base
        """
        # 1. Verifier ownership du control_result
        self._verify_control_result_ownership(db, control_result_id, user_id)

        # 2. Chiffrer avec envelope encryption
        encrypted_data, encrypted_dek, dek_nonce = self.envelope.encrypt_file(content)

        # 3. Generer UUID et ecrire sur disque
        file_uuid = str(uuid4())
        blobs_dir = _get_blobs_dir()
        file_path = blobs_dir / f"{file_uuid}.enc"
        file_path.write_bytes(encrypted_data)

        # 4. Creer l'Attachment en base
        attachment = Attachment(
            control_result_id=control_result_id,
            file_uuid=file_uuid,
            original_filename=filename,
            stored_filename=f"{file_uuid}.enc",
            file_path=f"blobs/{file_uuid}.enc",
            mime_type=content_type or "application/octet-stream",
            file_size=len(content),
            description=description,
            uploaded_by=str(user_id),
            encrypted_dek=encrypted_dek if encrypted_dek else None,
            dek_nonce=dek_nonce if dek_nonce else None,
            kek_version=1 if self.envelope.enabled else None,
        )
        db.add(attachment)
        db.flush()
        db.refresh(attachment)

        logger.info(
            "Fichier uploade: %s (%d octets) -> blobs/%s.enc par user %s",
            filename,
            len(content),
            file_uuid,
            user_id,
        )
        return attachment

    def download_file(self, db: Session, attachment_id: int, user_id: int) -> tuple[bytes, str, str]:
        """
        Dechiffre et retourne un fichier avec verification d'ownership.

        Gere deux cas :
        - Nouveau fichier (encrypted_dek present) : dechiffrement envelope
        - Ancien fichier (pas de encrypted_dek) : lecture directe depuis file_path

        Returns:
            (content_bytes, original_filename, mime_type)
        """
        attachment = self._get_attachment_with_ownership(db, attachment_id, user_id)

        # Detecter si c'est un fichier nouveau (stocke dans blobs/) ou ancien (file_path legacy)
        blobs_dir = _get_blobs_dir()
        blob_path = blobs_dir / f"{attachment.file_uuid}.enc" if attachment.file_uuid else None
        is_new_system = blob_path is not None and blob_path.exists()

        if is_new_system:
            raw_data = blob_path.read_bytes()
            if attachment.encrypted_dek is not None and len(attachment.encrypted_dek) > 0:
                # Fichier chiffre : dechiffrer avec envelope
                content = self.envelope.decrypt_file(raw_data, attachment.encrypted_dek, attachment.dek_nonce)
            else:
                # Fichier en mode passthrough (dev) : pas de chiffrement
                content = raw_data
        else:
            # Ancien systeme : fichier non chiffre a file_path
            settings = get_settings()
            base_data = Path(settings.FRAMEWORKS_DIR).parent / "data"
            file_path = (base_data / attachment.file_path).resolve()

            # Protection path traversal
            if not file_path.is_relative_to(base_data.resolve()):
                raise NotFoundError("Fichier introuvable")

            try:
                content = file_path.read_bytes()
            except FileNotFoundError:
                raise NotFoundError("Fichier introuvable sur le disque")

        return content, attachment.original_filename, attachment.mime_type

    def delete_file(self, db: Session, attachment_id: int, user_id: int) -> None:
        """Supprime un fichier (disque + base) avec verification d'ownership."""
        attachment = self._get_attachment_with_ownership(db, attachment_id, user_id)

        # Determiner le chemin du fichier sur disque
        blobs_dir = _get_blobs_dir()
        blob_path = blobs_dir / f"{attachment.file_uuid}.enc" if attachment.file_uuid else None

        if blob_path is not None and blob_path.exists():
            file_path = blob_path
        else:
            settings = get_settings()
            base_data = Path(settings.FRAMEWORKS_DIR).parent / "data"
            file_path = (base_data / attachment.file_path).resolve()

        try:
            file_path.unlink()
            logger.info("Fichier supprime du disque: %s", file_path)
        except FileNotFoundError:
            logger.debug("Fichier deja absent du disque: %s", file_path)

        # Supprimer de la base
        db.delete(attachment)
        db.flush()
        logger.info("Attachment supprime: id=%d (%s)", attachment_id, attachment.original_filename)

    @staticmethod
    def get_control_result(db: Session, result_id: int) -> ControlResult | None:
        """Récupère un ControlResult par ID."""
        return db.query(ControlResult).filter(ControlResult.id == result_id).first()

    @staticmethod
    def get_assessment_with_hierarchy(db: Session, assessment_id: int) -> Assessment | None:
        """Récupère un Assessment avec équipement → site → entreprise chargés."""
        return (
            db.query(Assessment)
            .options(
                joinedload(Assessment.equipement)
                .joinedload(Equipement.site)
                .joinedload(Site.entreprise)
            )
            .filter(Assessment.id == assessment_id)
            .first()
        )

    @staticmethod
    def get_attachment_for_user(db: Session, attachment_id: int, user: User) -> Attachment:
        """
        Récupère un Attachment avec vérification d'ownership admin-aware.
        Admins voient tout. Lève NotFoundError si introuvable.
        """
        query = db.query(Attachment).filter(Attachment.id == attachment_id)
        if user.role != "admin":
            query = (
                query.join(ControlResult, Attachment.control_result_id == ControlResult.id)
                .join(Assessment, ControlResult.assessment_id == Assessment.id)
                .join(AssessmentCampaign, Assessment.campaign_id == AssessmentCampaign.id)
                .join(Audit, AssessmentCampaign.audit_id == Audit.id)
                .filter(Audit.owner_id == user.id)
            )
        att = query.first()
        if att is None:
            raise NotFoundError("Pièce jointe introuvable")
        return att

    @staticmethod
    def list_attachments_for_result(db: Session, result_id: int, user: User) -> list[Attachment]:
        """Liste les pièces jointes d'un ControlResult avec RBAC admin-aware."""
        query = db.query(Attachment).filter(Attachment.control_result_id == result_id)
        if user.role != "admin":
            query = (
                query.join(ControlResult, Attachment.control_result_id == ControlResult.id)
                .join(Assessment, ControlResult.assessment_id == Assessment.id)
                .join(AssessmentCampaign, Assessment.campaign_id == AssessmentCampaign.id)
                .join(Audit, AssessmentCampaign.audit_id == Audit.id)
                .filter(Audit.owner_id == user.id)
            )
        return query.order_by(Attachment.uploaded_at.desc()).all()

    @staticmethod
    def save_attachment(db: Session, attachment: Attachment) -> Attachment:
        """Persiste un Attachment en base."""
        db.add(attachment)
        db.flush()
        db.refresh(attachment)
        return attachment

    @staticmethod
    def delete_attachment_record(db: Session, attachment: Attachment) -> None:
        """Supprime un Attachment de la base."""
        db.delete(attachment)
        db.flush()
