from fastapi import APIRouter

from ficus.routers.confierge import router as confierge_router
from ficus.routers.files import router as file_crud_router

# from ficus.routers.configs import router as config_router

# router = APIRouter(prefix="/v1")

# router.include_router(config_router)
router = APIRouter(prefix="/v1")
router.include_router(confierge_router)
router.include_router(file_crud_router)
