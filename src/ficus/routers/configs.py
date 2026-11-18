from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigDataResponse, ConfigResponse, DryRunResponse
from ficus.services.configs import (
    DEFAULT_MODE,
    VALID_EXTENSIONS_TYPE,
    get_config,
    save_config,
    update_config,
    delete_config,
    get_all_modes,
)
from ficus.services.preview import dry_run_save_config, preview_config
from ficus.utils.dict_merge import _deep_update
from .utils import data_store

router = APIRouter(prefix="/configs")


class PreviewRequest(BaseModel):
    path: Path
    data: dict

# We want to support arbitrary scopes passed in as query parameters but there's not a natural way
# to set that up with how fastapi, as it assumes dict arguments are passed in the body.
# We can parse out query params matching scope names manually though.
def _parse_scopes(request: Request, data_store: DataStore = Depends(data_store)) -> dict[str, str]:
    """Check query parameters for Parse query parameters into a dict of scope identifiers.

    Example: ``?hostname=host1&subject_id=123``.
    """
    return {k: v for k, v in request.query_params.items() if k in data_store.scopes}

# Since we're parsing scopes manually, FastAPI doesn't know to add scopes to the openapi spec,
# so we have to tell it by injecting this bit into each endpoint's openapi_extra.
scope_params_openapi = {
    "parameters": [
        {
            "name": "scopes",
            "in": "query",
            "required": False,
            "schema": {
                "type": "object",
                "default": {}
            },
            "description": "Scope identifiers as query parameters. Example: `?hostname=host1&subject_id=123`",
        }
    ]
}

@router.get("/{namespace}", openapi_extra=scope_params_openapi)
def get_config_endpoint(
    namespace: str,
    mode: str = DEFAULT_MODE,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
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


@router.post("/{namespace}", openapi_extra=scope_params_openapi)
def save_config_endpoint(
    data: dict,
    namespace: str,
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    create_missing_namespace: bool = True,
    dry_run: bool = False,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse | DryRunResponse:
    try:
        if dry_run:
            return DryRunResponse(changes=dry_run_save_config(
                data_store,
                namespace=namespace,
                mode=mode,
                scope_identifiers=scope_identifiers,
                data=data,
                suffix=suffix,
                overwrite_defaults=overwrite_defaults,
                append_new_fields_to_last_scope=append_new_fields_to_last_scope,
                create_missing_namespace=create_missing_namespace,
            ))
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


@router.patch("/{namespace}", openapi_extra=scope_params_openapi)
def update_config_endpoint(
    data: dict,
    namespace: str,
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    dry_run: bool = False,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
    data_store: DataStore = Depends(data_store),
) -> ConfigResponse | DryRunResponse:
    try:
        if dry_run:
            current = get_config(
                data_store, namespace, mode=mode, scope_identifiers=scope_identifiers
            )
            return DryRunResponse(changes=dry_run_save_config(
                data_store,
                namespace=namespace,
                mode=mode,
                scope_identifiers=scope_identifiers,
                data=_deep_update(current.data, data),
                suffix=suffix,
                overwrite_defaults=overwrite_defaults,
                append_new_fields_to_last_scope=append_new_fields_to_last_scope,
            ))
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


@router.post("/{namespace}/preview", openapi_extra=scope_params_openapi)
def preview_config_endpoint(
    namespace: str,
    draft: PreviewRequest,
    mode: str = DEFAULT_MODE,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
    data_store: DataStore = Depends(data_store),
) -> ConfigDataResponse:
    try:
        config = preview_config(
            data_store, namespace, draft.path, draft.data, mode, scope_identifiers
        )
        return ConfigDataResponse(message="Successfully previewed configuration", config=config)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/{namespace}", openapi_extra=scope_params_openapi)
def delete_config_endpoint(
    namespace: str,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
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


@router.get("/{namespace}/modes")
def get_all_modes_endpoint(
    namespace: str,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
    lowest_scope_only: bool = True,
    data_store: DataStore = Depends(data_store),
) -> list[str]:
    try:
        modes = get_all_modes(
            data_store,
            namespace=namespace,
            scope_identifiers=scope_identifiers,
            lowest_scope_only=lowest_scope_only
        )
        return sorted(list(modes))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
