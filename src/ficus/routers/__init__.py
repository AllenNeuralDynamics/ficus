from fastapi import APIRouter, Depends, HTTPException, Request, status
from ficus.core.config import Settings as FicusSettings
from ficus.database.data_store import DataStore
from ficus.services.discovery import list_namespaces, list_scope_identifiers
from ficus.services.scopes import InvalidScopeNameError, ScopeExistsError, add_scope
from ficus.routers.configs import router as configs_router
from ficus.routers.leaves import router as leaves_router
from ficus.routers.utils import data_store

router = APIRouter(prefix="/v1")


@router.get("/scopes")
def get_scopes(data_store: DataStore = Depends(data_store)) -> list[str]:
    """The scopes in precedence order: configs merge defaults, then these (later wins)."""
    return data_store.reload_scopes()


@router.post("/scopes/{scope}", status_code=status.HTTP_201_CREATED)
def create_scope(scope: str, data_store: DataStore = Depends(data_store)) -> list[str]:
    """Create a scope (the only way to: saving a config never does). It goes last in the precedence.

    Returns the new precedence. 409 if it exists; 422 for a reserved or malformed name.
    """
    try:
        return add_scope(data_store, scope)
    except ScopeExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InvalidScopeNameError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/namespaces")
def get_namespaces(data_store: DataStore = Depends(data_store)) -> list[str]:
    return list_namespaces(data_store)


@router.get("/scopes/{scope}")
def get_scope_identifiers(
    scope: str, namespace: str | None = None, data_store: DataStore = Depends(data_store)
) -> list[str]:
    try:
        return list_scope_identifiers(data_store, scope, namespace)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

@router.get("/settings")
def get_settings(request: Request) -> FicusSettings:
        return request.app.state.settings


router.include_router(configs_router)
router.include_router(leaves_router)
