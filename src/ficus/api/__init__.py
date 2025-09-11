from fastapi import APIRouter

from ficus.api.v1beta import router as v1_router

router = APIRouter(prefix="/api")

router.include_router(v1_router)
