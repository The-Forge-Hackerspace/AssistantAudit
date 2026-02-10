"""
Routes Frameworks (Référentiels) : CRUD, import/export YAML.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.database import get_db
from ...core.deps import get_current_user, get_current_admin, PaginationParams
from ...models.user import User
from ...schemas.framework import FrameworkRead, FrameworkSummary
from ...schemas.common import PaginatedResponse, MessageResponse
from ...services.framework_service import FrameworkService

router = APIRouter()
settings = get_settings()


@router.get("", response_model=PaginatedResponse[FrameworkSummary])
async def list_frameworks(
    pagination: PaginationParams = Depends(),
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les référentiels disponibles"""
    frameworks, total = FrameworkService.list_frameworks(
        db, active_only=active_only, offset=pagination.offset, limit=pagination.page_size
    )
    return PaginatedResponse(
        items=frameworks,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/{framework_id}", response_model=FrameworkRead)
async def get_framework(
    framework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Détail d'un référentiel avec toutes ses catégories et contrôles"""
    framework = FrameworkService.get_framework(db, framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Référentiel introuvable")
    return framework


@router.post("/import", response_model=MessageResponse)
async def import_all_frameworks(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Importe tous les référentiels YAML depuis le dossier frameworks/"""
    frameworks_dir = Path(settings.FRAMEWORKS_DIR)
    if not frameworks_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dossier de frameworks introuvable : {frameworks_dir}",
        )
    frameworks = FrameworkService.import_all_from_directory(db, frameworks_dir)
    return MessageResponse(
        message=f"{len(frameworks)} référentiel(s) importé(s)",
        detail=", ".join(f.ref_id for f in frameworks),
    )


@router.post("/import/{filename}", response_model=FrameworkRead)
async def import_single_framework(
    filename: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Importe un référentiel YAML spécifique"""
    yaml_path = Path(settings.FRAMEWORKS_DIR) / filename
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier '{filename}' introuvable")
    try:
        framework = FrameworkService.import_from_yaml(db, yaml_path)
        return framework
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
