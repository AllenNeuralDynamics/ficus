from fastapi import APIRouter, Depends, HTTPException, Request

from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigDataResponse, ConfigResponse
from ficus.services.configs import (
    DEFAULT_MODE,
    VALID_EXTENSIONS_TYPE,
    get_config,
    save_config,
    update_config,
    delete_config,
)
from ficus.core.config import settings
from .utils import data_store

# Create the router instance
router = APIRouter(prefix="/confierge")


# TODO: make it clearer how to pass scope identifiers in the request
@router.get("/{namespace}")
def get_config_endpoint(
    namespace: str,
    request: Request,
    mode: str = DEFAULT_MODE,
    data_store: DataStore = Depends(data_store),
) -> ConfigDataResponse:
    # Convert query parameters to a standard Python dictionary
    scope_identifiers = {
        k: v for k, v in dict(request.query_params).items() if k in settings.scopes
    }
    try:
        config = get_config(
            data_store,
            namespace,
            mode=mode,
            scope_identifiers=scope_identifiers,
        )

        return ConfigDataResponse(
            message="Successfully retrieved configuration",
            config=config,
        )
    except Exception as e:  # TODO: make services.configs.get_config only raise ConfigNotFoundError
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{namespace}")
def save_config_endpoint(
    data: dict,
    namespace: str,
    request: Request,
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    create_missing_namespace: bool = True,
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse:
    # Convert query parameters to a standard Python dictionary
    scope_identifiers = {
        k: v for k, v in dict(request.query_params).items() if k in settings.scopes
    }
    try:
        save_config(
            data_store,
            namespace,
            mode=mode,
            scope_identifiers=scope_identifiers,
            data=data,
            suffix=suffix,
            overwrite_defaults=overwrite_defaults,
            append_new_fields_to_last_scope=append_new_fields_to_last_scope,
            create_missing_namespace=create_missing_namespace,
        )

        return ConfigResponse(
            message="Successfully saved configuration file",
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{namespace}")
def update_config_endpoint(
    data: dict,
    namespace: str,
    request: Request,
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse:
    # Convert query parameters to a standard Python dictionary
    scope_identifiers = {
        k: v for k, v in dict(request.query_params).items() if k in settings.scopes
    }
    try:
        update_config(
            data_store,
            namespace,
            mode=mode,
            scope_identifiers=scope_identifiers,
            data=data,
            new_suffix=suffix,
            overwrite_defaults=overwrite_defaults,
            append_new_fields_to_last_scope=append_new_fields_to_last_scope,
        )

        return ConfigResponse(
            message="Successfully updated configuration file",
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{namespace}")
def delete_config_endpoint(
    namespace: str,
    request: Request,
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse:
    # Convert query parameters to a standard Python dictionary
    scope_identifiers = {
        k: v for k, v in dict(request.query_params).items() if k in settings.scopes
    }
    try:
        delete_config(
            data_store,
            namespace,
            scope_identifiers=scope_identifiers,
        )

        return ConfigResponse(
            message="Successfully deleted configuration file",
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
