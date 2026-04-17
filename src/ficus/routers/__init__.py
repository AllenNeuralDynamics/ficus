from fastapi import APIRouter

from ficus.routers.configs import router as config_router

router = APIRouter(prefix="/api")

router.include_router(config_router)
