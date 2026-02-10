"""
Route Health : vérification de l'état de l'application.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Vérifie que l'API est opérationnelle"""
    return {
        "status": "healthy",
        "service": "AssistantAudit API",
        "version": "2.0.0",
    }
