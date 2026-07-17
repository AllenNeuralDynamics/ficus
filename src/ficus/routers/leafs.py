from fastapi import APIRouter, Depends, HTTPException

from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigData
from ficus.services.leafs import (
    DEFAULT_MODE,
    SUFFIX_STR_TYPE,
    create_leaf_from_data,
    read_leaf,
    create_leaf,
    delete_leaf,
    read_leaf_data,
    update_leaf_data,
)

from .utils import data_store

# Create the router instance
router = APIRouter(prefix="/leafs")

@router.get("/scopes")
def get_scopes(data_store: DataStore = Depends(data_store)):
    return data_store.scopes

@router.get("/leaf")
def get_leaf(
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
) -> dict:
    try:
        content, suffix = read_leaf(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": content, "suffix": suffix}

@router.get("/leaf_data")
def get_leaf_data(
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
) -> dict:
    try:
        data = read_leaf_data(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return data


@router.post("/leaf")
def post_leaf(
    namespace: str,
    suffix: SUFFIX_STR_TYPE,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    content: str = "",
    overwrite: bool = False,
    data_store: DataStore = Depends(data_store),
):
    try:
        content = create_leaf(
            data_store,
            namespace,
            suffix,
            scope,
            scope_identifier,
            mode,
            content=content,
            overwrite=overwrite,
        )
    except FileExistsError:
        raise HTTPException(status_code=400, detail="File already exists")
    return {"content": content}

@router.post("/leaf_data")
def post_leaf_data(
    namespace: str,
    data: ConfigData,
    suffix: SUFFIX_STR_TYPE,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    overwrite: bool = False,
    data_store: DataStore = Depends(data_store),
):
    try:
        data = create_leaf_from_data(
            data_store,
            namespace,
            suffix=suffix,
            scope=scope,
            scope_identifier=scope_identifier,
            mode=mode,
            data=data,
            overwrite=overwrite,
        )
    except FileExistsError:
        raise HTTPException(status_code=400, detail="File already exists")
    return data

@router.patch("/leaf_data")
def patch_leaf_data(
    namespace: str,
    data: ConfigData,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
):
    try:
        updated_data = update_leaf_data(
            data_store,
            namespace,
            data=data,
            scope=scope,
            scope_identifier=scope_identifier,
            mode=mode,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return updated_data


@router.delete("/leaf")
def delete_leaf_endpoint(
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
):
    try:
        leaf_path = delete_leaf(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return {"leaf_path": str(leaf_path)}
