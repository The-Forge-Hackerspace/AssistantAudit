"""
Schémas Pydantic communs : pagination, réponses génériques.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Réponse paginée générique"""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    """Réponse simple avec message"""
    message: str
    detail: str | None = None
