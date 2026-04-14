"""
Route Health : vérification de l'état de l'application.
"""

from fastapi import APIRouter

from ...core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """État de l'API"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
