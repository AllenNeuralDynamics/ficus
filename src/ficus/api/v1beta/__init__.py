from fastapi import APIRouter

from ficus.api.v1beta.configs import router as configs_router

router = APIRouter(prefix="/v1beta")

router.include_router(configs_router)

