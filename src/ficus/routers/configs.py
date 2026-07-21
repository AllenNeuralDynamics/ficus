from fastapi import APIRouter, Depends, HTTPException, Query

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
from .utils import data_store

router = APIRouter(prefix="/configs")


def _parse_scope_identifiers(
    scope_identifiers: list[str] = Query(default=[]),
) -> dict[str, str]:
    """Parse repeated ``scope_identifiers=key:value`` query params into a dict.

    Example: ``?scope_identifiers=env:prod&scope_identifiers=region:us-east``
    """
    result = {}
    for item in scope_identifiers:
        if ":" not in item:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid scope_identifier '{item}': expected format 'key:value'",
            )
        k, v = item.split(":", 1)
        result[k] = v
    return result


@router.get("/{namespace}")
def get_config_endpoint(
    namespace: str,
    mode: str = DEFAULT_MODE,
    scope_identifiers: dict[str, str] = Depends(_parse_scope_identifiers),
    data_store: DataStore = Depends(data_store),
) -> ConfigDataResponse:
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
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    create_missing_namespace: bool = True,
    scope_identifiers: dict[str, str] = Depends(_parse_scope_identifiers),
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse:
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
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    scope_identifiers: dict[str, str] = Depends(_parse_scope_identifiers),
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse:
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
    scope_identifiers: dict[str, str] = Depends(_parse_scope_identifiers),
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse:
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
