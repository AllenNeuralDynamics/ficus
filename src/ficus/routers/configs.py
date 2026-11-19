from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ficus.core.exceptions import ConfigNotFoundError, InvalidNamespaceError, InvalidScopeError
from ficus.database.data_store import DataStore
from ficus.schemas.configs import (
    AcrossConfigResponse,
    ConfigDataResponse,
    ConfigResponse,
    DryRunResponse,
)
from ficus.services.configs import (
    DEFAULT_MODE,
    VALID_EXTENSIONS_TYPE,
    get_config,
    save_config,
    update_config,
    delete_config,
    get_all_modes,
)
from ficus.services.inspectors import resolve_across
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

@router.get("/{namespace}", openapi_extra=scope_params_openapi, response_model_exclude_unset=True)
def get_config_endpoint(
    namespace: str,
    mode: str = DEFAULT_MODE,
    include_leaves: bool = False,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
    data_store: DataStore = Depends(data_store),
) -> ConfigDataResponse:
    try:
        config = get_config(
            data_store,
            namespace,
            mode=mode,
            scope_identifiers=scope_identifiers,
            include_leaves=include_leaves,
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


@router.get("/{namespace}/across/{scope}")
def get_configs_across_scope(
    namespace: str,
    scope: str,
    mode: str = DEFAULT_MODE,
    fields: str | None = None,
    identifiers: str | None = None,
    data_store: DataStore = Depends(data_store),
) -> AcrossConfigResponse:
    """Compare resolved fields across the identifiers of a scope.

    One item per identifier that has a leaf for `namespace`. `identifiers` (comma-separated)
    limits the items to those identifiers, in that order; an identifier with no folder resolves
    to the lower leaves (a new rig shows its defaults). `fields` is a comma-separated list of
    glom paths (`camera.frame_rate`); omit it to get every field. `values[field]` is the value
    that identifier resolves to, and `sources[field]` the leaf that set it (`scope: null` means
    the defaults). When a field resolves to an object, `sources` also names the leaf behind each
    field below it.

    A field no leaf sets has `values: null` **and** `sources: null`. A field a leaf sets to null
    has `values: null` and a non-null source. Without `fields`, each item lists its own fields,
    so items can differ; take the union for a table. An identifier whose leaf can't be read has
    `error` set and empty `values` and `sources`.
    """
    try:
        names = [name.strip() for name in fields.split(",") if name.strip()] if fields else None
        ids = [i.strip() for i in identifiers.split(",") if i.strip()] if identifiers else None
        return AcrossConfigResponse(
            items=resolve_across(data_store, namespace, scope, mode, names, ids)
        )
    except (InvalidScopeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (InvalidNamespaceError, ConfigNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
