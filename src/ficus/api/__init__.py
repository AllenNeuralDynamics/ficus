from fastapi import APIRouter

from ficus.api.v1beta import router as v1beta_router
from ficus.api.v2beta import router as v2beta_router

router = APIRouter(prefix="/api")

router.include_router(v1beta_router)
router.include_router(v2beta_router)
