"""
Router principal API v1 : agrège tous les sous-routers.
"""
from fastapi import APIRouter

from .auth import router as auth_router
from .entreprises import router as entreprises_router
from .audits import router as audits_router
from .sites import router as sites_router
from .equipements import router as equipements_router
from .frameworks import router as frameworks_router
from .assessments import router as assessments_router
from .attachments import router as attachments_router
from .scans import router as scans_router
from .tools import router as tools_router
from .pingcastle_terminal import router as pingcastle_ws_router
from .health import router as health_router
from .network_map import router as network_map_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentification"])
api_router.include_router(entreprises_router, prefix="/entreprises", tags=["Entreprises"])
api_router.include_router(audits_router, prefix="/audits", tags=["Audits"])
api_router.include_router(sites_router, prefix="/sites", tags=["Sites"])
api_router.include_router(equipements_router, prefix="/equipements", tags=["Équipements"])
api_router.include_router(frameworks_router, prefix="/frameworks", tags=["Référentiels"])
api_router.include_router(assessments_router, prefix="/assessments", tags=["Évaluations"])
api_router.include_router(attachments_router, prefix="/attachments", tags=["Pièces jointes"])
api_router.include_router(scans_router, prefix="/scans", tags=["Scanner réseau"])
api_router.include_router(network_map_router, prefix="/network-map", tags=["Cartographie réseau"])
api_router.include_router(tools_router)
api_router.include_router(pingcastle_ws_router)
