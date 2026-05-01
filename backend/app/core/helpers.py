"""
Utilitaires partages pour les routes et services.
Centralise les patterns repetes (404 checks, ownership, etc.).
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.audit import Audit
from .errors import NotFoundError


def get_or_404(db: Session, model, item_id: int, detail: str | None = None):
    """
    Recupere un objet par ID ou leve 404.
    Remplace le pattern repete :
        item = db.get(Model, id)
        if not item:
            raise HTTPException(status_code=404, detail="...")
    """
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail=detail or f"{model.__name__} introuvable",
        )
    return item


def check_owner(resource, owner_id: int, *, is_admin: bool = False) -> None:
    """
    Verifie que la ressource appartient au user.
    Admin bypass. Retourne 404 (pas 403) pour ne pas reveler l'existence.
    """
    if is_admin:
        return
    resource_owner = getattr(resource, "owner_id", None) or getattr(resource, "user_id", None)
    if resource_owner != owner_id:
        from .audit_logger import log_access_denied

        resource_type = type(resource).__name__
        resource_id = getattr(resource, "id", "?")
        log_access_denied(owner_id, resource_type, resource_id)
        raise HTTPException(status_code=404, detail=f"{resource_type} introuvable")


def check_audit_access(
    db: Session, audit_id: int, user_id: int, is_admin: bool
) -> Audit:
    """Recupere un audit en verifiant que l'utilisateur y a acces.

    Retourne 404 (et non 403) si l'utilisateur n'est pas proprietaire afin de
    ne pas reveler l'existence de la ressource.
    """
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise NotFoundError("Audit non trouve")
    if not is_admin and audit.owner_id != user_id:
        raise NotFoundError("Audit non trouve")
    return audit


def user_has_access_to_entreprise(db: Session, entreprise_id: int, user_id: int) -> bool:
    """Verifie si un user est proprietaire de l'entreprise ou a un audit lie."""
    from ..models.entreprise import Entreprise

    # Check direct ownership first (fast path)
    ent = db.get(Entreprise, entreprise_id)
    if ent and ent.owner_id == user_id:
        return True
    # Fallback: audit chain (backward compat)
    return (
        db.query(Audit)
        .filter(
            Audit.entreprise_id == entreprise_id,
            Audit.owner_id == user_id,
        )
        .first()
        is not None
    )
