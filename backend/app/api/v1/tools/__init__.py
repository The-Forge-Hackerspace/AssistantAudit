from fastapi import APIRouter

from .config_analysis import router as config_analysis_router
from .ssl_checker import router as ssl_checker_router
from .collect import router as collect_router
from .ad_audit import router as ad_audit_router
from .pingcastle import router as pingcastle_router
from .monkey365 import (
    router as monkey365_router,
    launch_monkey365_scan,
    list_monkey365_scans,
    get_monkey365_scan_result,
    delete_monkey365_scan,
)

router = APIRouter(prefix="/tools", tags=["tools"])

router.include_router(config_analysis_router)
router.include_router(ssl_checker_router)
router.include_router(collect_router)
router.include_router(ad_audit_router)
router.include_router(pingcastle_router)
router.include_router(monkey365_router)
