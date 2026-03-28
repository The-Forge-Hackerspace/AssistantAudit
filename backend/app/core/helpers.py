"""
Utilitaires partages pour les routes et services.
Centralise les patterns repetes (404 checks, ownership, etc.).
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session


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
