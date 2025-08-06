from fastapi import APIRouter

from calibration_api.api.v1.rigs import router as rigs_router
from calibration_api.api.v1.calibrations import router as calibrations_router
from calibration_api.api.v1.configs import router as configs_router

router = APIRouter(prefix="/v1beta")

router.include_router(rigs_router)
router.include_router(calibrations_router)
router.include_router(configs_router)

