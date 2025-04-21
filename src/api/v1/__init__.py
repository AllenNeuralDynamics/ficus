from fastapi import APIRouter

from src.api.v1.rigs import router as rigs_router
from src.api.v1.calibrations import router as calibrations_router
from src.api.v1.appconfigs import router as appconfigs_router

router = APIRouter(prefix="/v1")

router.include_router(rigs_router)
router.include_router(calibrations_router)
router.include_router(appconfigs_router)
