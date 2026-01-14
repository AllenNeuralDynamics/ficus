from fastapi import APIRouter

from ficus.api.v2beta.configs import router as configs_router

router = APIRouter(prefix="/v2beta")

router.include_router(configs_router)


