"""
Unified Enterprise API Router for Quality Inspection & RCA Platform
Aggregates modular domain routers under the /api prefix.
"""
from fastapi import APIRouter

from backend.app.routers.batches import router as batches_router
from backend.app.routers.inspection import router as inspection_router
from backend.app.routers.vision import router as vision_router
from backend.app.routers.process import router as process_router
from backend.app.routers.spc import router as spc_router
from backend.app.routers.rca import router as rca_router
from backend.app.routers.capa import router as capa_router
from backend.app.routers.orchestrator import router as orchestrator_router
from backend.app.routers.reports import router as reports_router
from backend.app.routers.scenarios import router as scenarios_router
from backend.app.routers.auth import router as auth_router

router = APIRouter(prefix="/api")

# Mount domain routers
router.include_router(auth_router)
router.include_router(batches_router)
router.include_router(inspection_router)
router.include_router(vision_router)
router.include_router(process_router)
router.include_router(spc_router)
router.include_router(rca_router)
router.include_router(capa_router)
router.include_router(orchestrator_router)
router.include_router(reports_router)
router.include_router(scenarios_router)

__all__ = ["router"]
