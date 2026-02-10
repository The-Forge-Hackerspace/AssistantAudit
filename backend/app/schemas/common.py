"""
Schémas Pydantic communs : pagination, réponses génériques.
"""
from typing import Generic, Optional, TypeVar

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


class ScoreResponse(BaseModel):
    """Score de conformité détaillé"""
    score: Optional[float] = None
    total_controls: int = 0
    assessed: int = 0
    compliant: int = 0
    non_compliant: int = 0
    partially_compliant: int = 0
    not_applicable: int = 0
    not_assessed: int = 0
    by_severity: dict = {}  # { "critical": {"total": 5, "compliant": 3, ...}, ... }
