"""
Router principal API v1 : agrège tous les sous-routers.
"""
from fastapi import APIRouter

from .auth import router as auth_router
from .entreprises import router as entreprises_router
from .audits import router as audits_router
from .frameworks import router as frameworks_router
from .assessments import router as assessments_router
from .health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentification"])
api_router.include_router(entreprises_router, prefix="/entreprises", tags=["Entreprises"])
api_router.include_router(audits_router, prefix="/audits", tags=["Audits"])
api_router.include_router(frameworks_router, prefix="/frameworks", tags=["Référentiels"])
api_router.include_router(assessments_router, prefix="/assessments", tags=["Évaluations"])
