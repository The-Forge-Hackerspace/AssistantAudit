"""
Routes Sites : CRUD des emplacements physiques.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, get_current_admin, PaginationParams
from ...models.entreprise import Entreprise
from ...models.site import Site
from ...models.user import User
from ...schemas.site import SiteCreate, SiteRead, SiteUpdate
from ...schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SiteRead])
async def list_sites(
    entreprise_id: int = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les sites (filtrable par entreprise)"""
    query = db.query(Site)
    if entreprise_id:
        query = query.filter(Site.entreprise_id == entreprise_id)
    total = query.count()
    items = query.order_by(Site.nom).offset(pagination.offset).limit(pagination.page_size).all()

    # Enrichir avec le nombre d'équipements
    result = []
    for site in items:
        site_data = SiteRead(
            id=site.id,
            nom=site.nom,
            description=site.description,
            adresse=site.adresse,
            entreprise_id=site.entreprise_id,
            equipement_count=len(site.equipements) if site.equipements else 0,
        )
        result.append(site_data)

    return PaginatedResponse(
        items=result,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Crée un nouveau site pour une entreprise"""
    # Vérifier que l'entreprise existe
    entreprise = db.get(Entreprise, body.entreprise_id)
    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    # Vérifier unicité nom+entreprise
    existing = (
        db.query(Site)
        .filter(Site.entreprise_id == body.entreprise_id, Site.nom == body.nom)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Le site '{body.nom}' existe déjà pour cette entreprise",
        )

    site = Site(nom=body.nom, description=body.description, adresse=body.adresse, entreprise_id=body.entreprise_id)
    db.add(site)
    db.commit()
    db.refresh(site)
    return SiteRead(
        id=site.id,
        nom=site.nom,
        description=site.description,
        adresse=site.adresse,
        entreprise_id=site.entreprise_id,
        equipement_count=0,
    )


@router.get("/{site_id}", response_model=SiteRead)
async def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Détail d'un site"""
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")
    return SiteRead(
        id=site.id,
        nom=site.nom,
        description=site.description,
        adresse=site.adresse,
        entreprise_id=site.entreprise_id,
        equipement_count=len(site.equipements) if site.equipements else 0,
    )


@router.put("/{site_id}", response_model=SiteRead)
async def update_site(
    site_id: int,
    body: SiteUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Modifie un site"""
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(site, field, value)

    db.commit()
    db.refresh(site)
    return SiteRead(
        id=site.id,
        nom=site.nom,
        description=site.description,
        adresse=site.adresse,
        entreprise_id=site.entreprise_id,
        equipement_count=len(site.equipements) if site.equipements else 0,
    )


@router.delete("/{site_id}", response_model=MessageResponse)
async def delete_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Supprime un site et ses équipements"""
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site introuvable")

    db.delete(site)
    db.commit()
    return MessageResponse(message=f"Site '{site.nom}' supprimé")
