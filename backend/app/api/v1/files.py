"""
Routes fichiers preuves chiffres — upload, download, suppression
avec chiffrement enveloppe (EnvelopeEncryption).

Coexiste avec attachments.py (legacy non chiffre).
Les nouveaux fichiers passent par ces routes ; les anciens restent accessibles
via le download qui detecte automatiquement le mode.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur
from ...models.user import User
from ...schemas.attachment import AttachmentRead
from ...services.file_service import FileService

logger = logging.getLogger(__name__)
router = APIRouter()

# Extensions autorisees (meme liste que attachments.py)
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".log", ".conf", ".cfg", ".ini", ".yaml", ".yml",
    ".json", ".xml", ".csv", ".md",
    ".zip", ".gz", ".tar",
    ".pcap", ".cap",
}

_file_service = FileService()


@router.post(
    "/upload",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_file(
    control_result_id: int = Form(...),
    file: UploadFile = File(...),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Upload un fichier preuve chiffre pour un resultat de controle."""
    settings = get_settings()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Verifier l'extension
    original_name = file.filename or "unknown"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension '{ext}' non autorisee.",
        )

    # Lire en chunks pour limiter la memoire
    chunks = []
    total_size = 0
    while True:
        chunk = file.file.read(8192)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux (>{settings.MAX_UPLOAD_SIZE_MB} Mo).",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    mime = file.content_type or "application/octet-stream"

    attachment = _file_service.upload_file(
        db=db,
        content=content,
        filename=original_name,
        content_type=mime,
        control_result_id=control_result_id,
        user_id=current_user.id,
        description=description,
    )
    db.flush()
    db.refresh(attachment)

    result = AttachmentRead.model_validate(attachment)
    result.download_url = f"/api/v1/files/download/{attachment.id}"
    return result


@router.get("/download/{attachment_id}")
def download_file(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Telecharge un fichier preuve (dechiffrement automatique)."""
    content, filename, mime_type = _file_service.download_file(
        db=db,
        attachment_id=attachment_id,
        user_id=current_user.id,
    )
    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
):
    """Supprime un fichier preuve (disque + base)."""
    _file_service.delete_file(
        db=db,
        attachment_id=attachment_id,
        user_id=current_user.id,
    )
