from fastapi import APIRouter, Depends, HTTPException, Query

from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigData
from ficus.services.leafs import (
    create_leaf_from_data,
    read_leaf,
    create_leaf,
    delete_leaf,
    read_leaf_data,
    update_leaf_data,
)
from ficus.services.utils import DEFAULT_MODE, DEFAULT_SUFFIX, SUFFIX_STR_TYPE

from .utils import data_store

router = APIRouter(prefix="/leaves")


def _validate_scope_pair(
    scope: str | None = Query(default=None),
    scope_identifier: str | None = Query(default=None),
) -> tuple[str | None, str | None]:
    """Require that scope and scope_identifier are always provided together."""
    if (scope is None) != (scope_identifier is None):
        raise HTTPException(
            status_code=422,
            detail="scope and scope_identifier must both be provided or both be omitted",
        )
    return scope, scope_identifier


@router.get("/{namespace}")
def get_leaf_data(
    namespace: str,
    scope_pair: tuple[str | None, str | None] = Depends(_validate_scope_pair),
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
) -> dict:
    scope, scope_identifier = scope_pair
    try:
        data = read_leaf_data(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return data


@router.get("/{namespace}/raw")
def get_leaf_raw(
    namespace: str,
    scope_pair: tuple[str | None, str | None] = Depends(_validate_scope_pair),
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
) -> dict:
    scope, scope_identifier = scope_pair
    try:
        content, suffix = read_leaf(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": content, "suffix": suffix}


@router.post("/{namespace}")
def post_leaf_data(
    namespace: str,
    data: ConfigData,
    suffix: SUFFIX_STR_TYPE,
    scope_pair: tuple[str | None, str | None] = Depends(_validate_scope_pair),
    mode: str = DEFAULT_MODE,
    overwrite: bool = False,
    data_store: DataStore = Depends(data_store),
):
    scope, scope_identifier = scope_pair
    try:
        result = create_leaf_from_data(
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
        raise HTTPException(status_code=409, detail="Leaf already exists")
    return result


@router.post("/{namespace}/raw")
def post_leaf_raw(
    namespace: str,
    suffix: SUFFIX_STR_TYPE = DEFAULT_SUFFIX,
    scope_pair: tuple[str | None, str | None] = Depends(_validate_scope_pair),
    mode: str = DEFAULT_MODE,
    content: str = "",
    overwrite: bool = False,
    data_store: DataStore = Depends(data_store),
):
    scope, scope_identifier = scope_pair
    try:
        result = create_leaf(
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
        raise HTTPException(status_code=409, detail="Leaf already exists")
    return {"content": result}


@router.patch("/{namespace}")
def patch_leaf_data(
    namespace: str,
    data: ConfigData,
    scope_pair: tuple[str | None, str | None] = Depends(_validate_scope_pair),
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
):
    scope, scope_identifier = scope_pair
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


@router.delete("/{namespace}")
def delete_leaf_endpoint(
    namespace: str,
    scope_pair: tuple[str | None, str | None] = Depends(_validate_scope_pair),
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
):
    scope, scope_identifier = scope_pair
    try:
        leaf_path = delete_leaf(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return {"leaf_path": str(leaf_path)}
