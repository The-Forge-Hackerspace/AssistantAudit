"""
Schémas Attachment — Pièces jointes des résultats de contrôle.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AttachmentRead(BaseModel):
    id: int
    control_result_id: int
    original_filename: str
    stored_filename: str
    file_path: str
    mime_type: str
    file_size: int
    description: Optional[str] = None
    uploaded_at: datetime
    uploaded_by: Optional[str] = None

    # URL calculée côté API
    download_url: Optional[str] = None
    preview_url: Optional[str] = None

    model_config = {"from_attributes": True}


class AttachmentCreate(BaseModel):
    """Envoyé en multipart, mais la description peut venir en form field"""

    description: Optional[str] = None
