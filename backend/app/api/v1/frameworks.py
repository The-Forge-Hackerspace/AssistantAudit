"""
Routes Frameworks (Référentiels) : CRUD, import/export YAML, versioning.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.database import get_db
from ...core.deps import get_current_user, get_current_admin, get_current_auditeur, PaginationParams
from ...models.user import User
from ...schemas.framework import FrameworkRead, FrameworkSummary, FrameworkCloneRequest
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


@router.get("/{framework_id}/versions", response_model=list[FrameworkSummary])
async def list_framework_versions(
    framework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste toutes les versions d'un référentiel"""
    framework = FrameworkService.get_framework(db, framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Référentiel introuvable")
    versions = FrameworkService.list_versions(db, framework.ref_id)
    return versions


@router.post("/{framework_id}/clone", response_model=FrameworkRead, status_code=status.HTTP_201_CREATED)
async def clone_framework(
    framework_id: int,
    body: FrameworkCloneRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Clone un référentiel en nouvelle version (désactive l'ancienne)"""
    try:
        clone = FrameworkService.clone_as_new_version(
            db, framework_id, new_version=body.new_version, new_name=body.new_name
        )
        return clone
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{framework_id}/export")
async def export_framework(
    framework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Exporte un référentiel en fichier YAML"""
    framework = FrameworkService.get_framework(db, framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Référentiel introuvable")

    output_dir = Path(settings.UPLOAD_DIR) / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{framework.ref_id}_v{framework.version}.yaml"
    output_path = output_dir / filename

    try:
        FrameworkService.export_to_yaml(db, framework_id, output_path)
        return FileResponse(
            path=str(output_path),
            filename=filename,
            media_type="application/x-yaml",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
