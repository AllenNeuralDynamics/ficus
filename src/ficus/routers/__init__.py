from fastapi import APIRouter

from ficus.routers.configs import router as config_router

router = APIRouter(prefix="/v1")

router.include_router(config_router)
