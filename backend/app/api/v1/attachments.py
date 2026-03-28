"""
Routes Attachments : upload, download, suppression de pièces jointes
liées aux résultats de contrôle.

Structure de stockage :
  data/{entreprise_nom}/{site_nom}/{equipement_identifiant}/
"""
import logging
import mimetypes
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from ...core.config import get_settings
from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur
from ...models.user import User
from ...models.assessment import ControlResult, Assessment, AssessmentCampaign
from ...models.audit import Audit
from ...models.equipement import Equipement
from ...models.site import Site
from ...models.entreprise import Entreprise
from ...models.attachment import Attachment
from ...schemas.attachment import AttachmentRead

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_attachment_with_ownership(
    db: Session, attachment_id: int, user: User
) -> Attachment:
    """
    Recupere un Attachment avec verification d'ownership via la chaine :
    Attachment -> ControlResult -> Assessment -> Campaign -> Audit -> owner_id.
    Admins voient tout. Retourne 404 (pas 403) si non trouve.
    """
    query = db.query(Attachment).filter(Attachment.id == attachment_id)
    if user.role != "admin":
        query = (
            query
            .join(ControlResult, Attachment.control_result_id == ControlResult.id)
            .join(Assessment, ControlResult.assessment_id == Assessment.id)
            .join(AssessmentCampaign, Assessment.campaign_id == AssessmentCampaign.id)
            .join(Audit, AssessmentCampaign.audit_id == Audit.id)
            .filter(Audit.owner_id == user.id)
        )
    att = query.first()
    if att is None:
        raise HTTPException(status_code=404, detail="Piece jointe introuvable")
    return att

# Extensions autorisées
ALLOWED_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Texte / Config
    ".txt", ".log", ".conf", ".cfg", ".ini", ".yaml", ".yml",
    ".json", ".xml", ".csv", ".md",
    # Archives
    ".zip", ".gz", ".tar",
    # Réseau / Sécurité
    ".pcap", ".cap",
}

# Types MIME prévisualisables inline
PREVIEWABLE_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp", "image/svg+xml"}
PREVIEWABLE_TEXT_TYPES = {
    "text/plain", "text/csv", "text/markdown",
    "application/json", "application/xml", "text/xml",
    "application/x-yaml", "text/yaml",
}


def _sanitize_dirname(name: str) -> str:
    """Transforme un nom en nom de dossier sûr pour le filesystem."""
    # Remplacer les caractères dangereux
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe.strip('. _')
    return safe or "unknown"


def _build_storage_path(db: Session, control_result: ControlResult) -> Path:
    """
    Construit le chemin de stockage :
      data/{entreprise_nom}/{site_nom}/{equipement_id}/
    en suivant la chaîne : ControlResult → Assessment → Equipement → Site → Entreprise
    """
    # Charger la chaîne complète avec joinedload pour éviter les lazy-load issues
    assessment = (
        db.query(Assessment)
        .options(
            joinedload(Assessment.equipement)
            .joinedload(Equipement.site)
            .joinedload(Site.entreprise)
        )
        .filter(Assessment.id == control_result.assessment_id)
        .first()
    )
    if not assessment or not assessment.equipement:
        raise HTTPException(status_code=500, detail="Impossible de résoudre le chemin de stockage")

    equipement = assessment.equipement
    site = equipement.site
    if not site:
        raise HTTPException(status_code=500, detail="Site introuvable pour cet équipement")
    entreprise = site.entreprise
    if not entreprise:
        raise HTTPException(status_code=500, detail="Entreprise introuvable pour ce site")

    entreprise_dir = _sanitize_dirname(entreprise.nom)
    site_dir = _sanitize_dirname(site.nom)

    # Utiliser hostname si disponible, sinon IP
    equip_label = equipement.hostname or equipement.ip_address
    equip_dir = _sanitize_dirname(equip_label)

    settings = get_settings()
    base = Path(settings.FRAMEWORKS_DIR).parent / "data"  # = AssistantAudit/data
    storage_path = base / entreprise_dir / site_dir / equip_dir

    return storage_path


def _attachment_to_read(att: Attachment, request_base: str = "") -> AttachmentRead:
    """Convertir un Attachment en schema de lecture avec URLs."""
    read = AttachmentRead.model_validate(att)
    prefix = f"/api/v1/attachments/{att.id}"
    read.download_url = f"{prefix}/download"

    # Preview possible pour images et texte
    if att.mime_type in PREVIEWABLE_IMAGE_TYPES or att.mime_type in PREVIEWABLE_TEXT_TYPES:
        read.preview_url = f"{prefix}/preview"

    return read


# ── Upload ──

@router.post(
    "/control-result/{result_id}/upload",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    result_id: int,
    file: UploadFile = File(...),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Upload un fichier (capture d'écran, config, etc.) pour un résultat de contrôle."""
    settings = get_settings()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Vérifier que le control result existe
    cr = db.query(ControlResult).filter(ControlResult.id == result_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Résultat de contrôle introuvable")

    # Vérifier l'extension
    original_name = file.filename or "unknown"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension '{ext}' non autorisée. Extensions autorisées : {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Lire le contenu en streaming pour éviter l'épuisement mémoire
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux (>{settings.MAX_UPLOAD_SIZE_MB} Mo). Maximum : {settings.MAX_UPLOAD_SIZE_MB} Mo",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    # Construire le chemin de stockage
    storage_dir = _build_storage_path(db, cr)
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Nom unique pour éviter les conflits
    stored_name = f"{uuid.uuid4().hex[:12]}_{original_name}"
    stored_name = re.sub(r'[<>:"/\\|?*]', '_', stored_name)  # sanitize
    file_path = storage_dir / stored_name
    file_path.write_bytes(content)

    # Calculer le chemin relatif depuis le dossier data/
    base_data = Path(settings.FRAMEWORKS_DIR).parent / "data"
    rel_path = str(file_path.relative_to(base_data))

    # Déterminer le type MIME
    mime = file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"

    # Sauvegarder en base
    attachment = Attachment(
        control_result_id=result_id,
        original_filename=original_name,
        stored_filename=stored_name,
        file_path=rel_path,
        mime_type=mime,
        file_size=len(content),
        description=description,
        uploaded_by=current_user.username,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    logger.info(
        f"Attachment uploaded: {original_name} ({len(content)} bytes) "
        f"→ {rel_path} by {current_user.username}"
    )

    return _attachment_to_read(attachment)


# ── List ──

@router.get(
    "/control-result/{result_id}",
    response_model=list[AttachmentRead],
)
async def list_attachments(
    result_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les pièces jointes d'un résultat de contrôle."""
    cr = db.query(ControlResult).filter(ControlResult.id == result_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Résultat de contrôle introuvable")

    attachments = (
        db.query(Attachment)
        .filter(Attachment.control_result_id == result_id)
        .order_by(Attachment.uploaded_at.desc())
        .all()
    )
    return [_attachment_to_read(a) for a in attachments]


# ── Download ──

@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Telecharge un fichier joint (avec verification d'ownership)."""
    att = _get_attachment_with_ownership(db, attachment_id, current_user)

    settings = get_settings()
    base_data = Path(settings.FRAMEWORKS_DIR).parent / "data"
    file_path = (base_data / att.file_path).resolve()

    # Protection contre le path traversal — 404 pour ne pas reveler l'existence
    if not file_path.is_relative_to(base_data.resolve()):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le disque")

    return FileResponse(
        path=str(file_path),
        filename=att.original_filename,
        media_type=att.mime_type,
    )


# ── Preview (inline) ──

@router.get("/{attachment_id}/preview")
async def preview_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Previsualise un fichier (image ou texte) inline dans le navigateur."""
    att = _get_attachment_with_ownership(db, attachment_id, current_user)

    if att.mime_type not in PREVIEWABLE_IMAGE_TYPES and att.mime_type not in PREVIEWABLE_TEXT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Ce type de fichier ne peut pas être prévisualisé",
        )

    settings = get_settings()
    base_data = Path(settings.FRAMEWORKS_DIR).parent / "data"
    file_path = (base_data / att.file_path).resolve()

    # Protection contre le path traversal — 404 pour ne pas reveler l'existence
    if not file_path.is_relative_to(base_data.resolve()):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le disque")

    # Pour la preview inline, on ne force pas le téléchargement
    return FileResponse(
        path=str(file_path),
        media_type=att.mime_type,
        # Pas de content-disposition attachment → s'affiche inline
    )


# ── Delete ──

@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Supprime une piece jointe (fichier + entree BDD) avec verification d'ownership."""
    att = _get_attachment_with_ownership(db, attachment_id, current_user)

    # Supprimer le fichier physique
    settings = get_settings()
    base_data = Path(settings.FRAMEWORKS_DIR).parent / "data"
    file_path = (base_data / att.file_path).resolve()

    # Protection contre le path traversal — 404 pour ne pas reveler l'existence
    if not file_path.is_relative_to(base_data.resolve()):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    if file_path.exists():
        file_path.unlink()
        logger.info(f"Attachment file deleted: {att.file_path}")

        # Supprimer les dossiers vides en remontant
        parent = file_path.parent
        while parent != base_data:
            try:
                parent.rmdir()  # ne supprime que si vide
                parent = parent.parent
            except OSError:
                break

    # Supprimer de la base
    db.delete(att)
    db.commit()
    logger.info(f"Attachment record deleted: id={attachment_id} ({att.original_filename})")
