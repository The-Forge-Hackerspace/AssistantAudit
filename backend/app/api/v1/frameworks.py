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
from ...schemas.framework import FrameworkRead, FrameworkSummary, FrameworkCloneRequest, FrameworkCreate
from ...schemas.common import PaginatedResponse, MessageResponse
from ...services.framework_service import FrameworkService

router = APIRouter()
settings = get_settings()


@router.get("", response_model=PaginatedResponse[FrameworkSummary])
def list_frameworks(
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
def get_framework(
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
def list_framework_versions(
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
def clone_framework(
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
def export_framework(
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


@router.post("/sync", response_model=MessageResponse)
def sync_frameworks(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Synchronise les référentiels YAML → BDD.
    Détecte automatiquement les fichiers nouveaux ou modifiés.
    Les fichiers inchangés sont ignorés (comparaison par hash SHA-256).
    Admin uniquement.
    """
    frameworks_dir = Path(settings.FRAMEWORKS_DIR)
    if not frameworks_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dossier de frameworks introuvable : {frameworks_dir}",
        )
    result = FrameworkService.sync_from_directory(db, frameworks_dir)
    total = result['imported'] + result['updated'] + result['unchanged']
    return MessageResponse(
        message=(
            f"{total} référentiel(s) traité(s) : "
            f"{result['imported']} nouveau(x), "
            f"{result['updated']} mis à jour, "
            f"{result['unchanged']} inchangé(s)"
        ),
    )


@router.post("", response_model=FrameworkRead, status_code=status.HTTP_201_CREATED)
def create_framework(
    body: FrameworkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Crée un nouveau référentiel depuis l'éditeur (admin uniquement)"""
    categories_data = []
    for cat in body.categories:
        cat_dict = {"name": cat.name, "description": cat.description, "controls": []}
        for ctrl in cat.controls:
            cat_dict["controls"].append(ctrl.model_dump())
        categories_data.append(cat_dict)
    try:
        framework = FrameworkService.create_framework(
            db,
            ref_id=body.ref_id,
            name=body.name,
            version=body.version,
            description=body.description,
            engine=body.engine,
            engine_config=body.engine_config,
            source=body.source,
            author=body.author,
            categories=categories_data,
        )
        return framework
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{framework_id}", response_model=FrameworkRead)
def update_framework(
    framework_id: int,
    body: FrameworkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Met à jour un référentiel existant (admin uniquement)"""
    data = body.model_dump()
    categories_data = []
    for cat in body.categories:
        cat_dict = {"name": cat.name, "description": cat.description, "controls": []}
        for ctrl in cat.controls:
            cat_dict["controls"].append(ctrl.model_dump())
        categories_data.append(cat_dict)
    data["categories"] = categories_data
    try:
        framework = FrameworkService.update_framework(db, framework_id, data)
        return framework
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{framework_id}", response_model=MessageResponse)
def delete_framework(
    framework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Supprime un référentiel (admin uniquement)"""
    try:
        FrameworkService.delete_framework(db, framework_id)
        return {"message": "Référentiel supprimé"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/import", response_model=MessageResponse)
def import_all_frameworks(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Importe (force) tous les référentiels YAML depuis le dossier frameworks/"""
    frameworks_dir = Path(settings.FRAMEWORKS_DIR)
    if not frameworks_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dossier de frameworks introuvable : {frameworks_dir}",
        )
    frameworks = FrameworkService.import_all_from_directory(db, frameworks_dir)
    return MessageResponse(
        message=f"{len(frameworks)} référentiel(s) importé(s)",
    )


@router.post("/import/{filename}", response_model=FrameworkRead)
def import_single_framework(
    filename: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Importe un référentiel YAML spécifique"""
    frameworks_dir = Path(settings.FRAMEWORKS_DIR).resolve()
    yaml_path = (frameworks_dir / filename).resolve()
    # Protection path traversal
    if not yaml_path.is_relative_to(frameworks_dir):
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier '{filename}' introuvable")
    try:
        framework = FrameworkService.import_from_yaml(db, yaml_path)
        return framework
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
