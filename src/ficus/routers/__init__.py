from fastapi import APIRouter, Depends, Request
from ficus.core.config import Settings as FicusSettings
from ficus.database.data_store import DataStore
from ficus.routers.configs import router as configs_router
from ficus.routers.leaves import router as leaves_router
from ficus.routers.utils import data_store

router = APIRouter(prefix="/v1")


@router.get("/scopes")
def get_scopes(data_store: DataStore = Depends(data_store)):
    return data_store.scopes

@router.get("/settings")
def get_settings(request: Request) -> FicusSettings:
        return request.app.state.settings


router.include_router(configs_router)
router.include_router(leaves_router)
