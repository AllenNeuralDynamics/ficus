from fastapi import APIRouter, Depends, HTTPException

from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigData
from ficus.services.file_crud import (
    DEFAULT_MODE,
    SUFFIX_STR_TYPE,
    create_file_from_data,
    read_file,
    create_file,
    delete_file,
    read_file_data,
    update_file_data,
)

from .utils import data_store

# Create the router instance
router = APIRouter(prefix="/file_crud")

@router.get("/scopes")
def get_scopes(data_store: DataStore = Depends(data_store)):
    return data_store.scopes

@router.get("/file")
def get_file(
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
) -> dict:
    try:
        content, suffix = read_file(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": content, "suffix": suffix}

@router.get("/file_data")
def get_file_data(
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
) -> dict:
    try:
        data = read_file_data(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return data


@router.post("/file")
def post_file(
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
        content = create_file(
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

@router.post("/file_data")
def post_file_data(
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
        data = create_file_from_data(
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

@router.patch("/file_data")
def patch_file_data(
    namespace: str,
    data: ConfigData,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
):
    try:
        updated_data = update_file_data(
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


@router.delete("/file")
def delete_file_endpoint(
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
):
    try:
        file_path = delete_file(data_store, namespace, scope, scope_identifier, mode)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_path": str(file_path)}
