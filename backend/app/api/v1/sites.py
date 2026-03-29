"""
Routes Sites : CRUD des emplacements physiques.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, get_current_admin, PaginationParams
from ...models.user import User
from ...schemas.site import SiteCreate, SiteRead, SiteUpdate
from ...schemas.common import PaginatedResponse, MessageResponse
from ...services.site_service import SiteService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SiteRead])
def list_sites(
    entreprise_id: int = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les sites (filtrable par entreprise)"""
    items, total = SiteService.list_sites(
        db,
        entreprise_id=entreprise_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
def create_site(
    body: SiteCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Crée un nouveau site pour une entreprise"""
    site = SiteService.create_site(db, body)
    return SiteRead(
        id=site.id,
        nom=site.nom,
        description=site.description,
        adresse=site.adresse,
        entreprise_id=site.entreprise_id,
        equipement_count=0,
    )


@router.get("/{site_id}", response_model=SiteRead)
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Détail d'un site"""
    site = SiteService.get_site(db, site_id)
    return SiteRead(
        id=site.id,
        nom=site.nom,
        description=site.description,
        adresse=site.adresse,
        entreprise_id=site.entreprise_id,
        equipement_count=len(site.equipements) if site.equipements else 0,
    )


@router.put("/{site_id}", response_model=SiteRead)
def update_site(
    site_id: int,
    body: SiteUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Modifie un site"""
    site = SiteService.update_site(db, site_id, body)
    return SiteRead(
        id=site.id,
        nom=site.nom,
        description=site.description,
        adresse=site.adresse,
        entreprise_id=site.entreprise_id,
        equipement_count=len(site.equipements) if site.equipements else 0,
    )


@router.delete("/{site_id}", response_model=MessageResponse)
def delete_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Supprime un site et ses équipements"""
    nom = SiteService.delete_site(db, site_id)
    return MessageResponse(message=f"Site '{nom}' supprimé")
