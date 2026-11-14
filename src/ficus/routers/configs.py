from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ficus.database.data_store import DataStore
from ficus.schemas.configs import AcrossConfigResponse, ConfigDataResponse, ConfigResponse
from ficus.services.configs import (
    DEFAULT_MODE,
    VALID_EXTENSIONS_TYPE,
    get_config,
    save_config,
    update_config,
    delete_config,
    get_all_modes,
)
from ficus.services.across import resolve_across
from .utils import data_store

router = APIRouter(prefix="/configs")

def _parse_scopes(request: Request, data_store: DataStore = Depends(data_store)) -> dict[str, str]:
    """Scope identifiers in Ficus's precedence (lowest first), whatever order the request lists them in.

    Two styles, not mixed: ``?scope=hostname:host1&scope=subject_id:123`` (any scope, no clash with
    other parameters) or the legacy ``?hostname=host1&subject_id=123``. A scope Ficus doesn't know
    (``scope=`` style), a repeated scope or a malformed pair is a 422; saving never creates a scope.
    """
    order = data_store.reload_scopes()
    pairs: list[tuple[str, str]] = []
    scoped = request.query_params.getlist("scope")
    legacy = [(k, v) for k, v in request.query_params.multi_items() if k in order]
    if scoped and legacy:
        raise HTTPException(
            status_code=422,
            detail="Use scope=<scope>:<identifier> or ?<scope>=<identifier>, not both.",
        )
    for raw in scoped:
        name, sep, identifier = raw.partition(":")
        if not sep or not name or not identifier:
            raise HTTPException(
                status_code=422, detail=f"Scope {raw!r} must be <scope>:<identifier>."
            )
        if name not in order:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown scope {name!r}. Known scopes: {', '.join(order)}.",
            )
        pairs.append((name, identifier))
    pairs += legacy
    names = [name for name, _ in pairs]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise HTTPException(
            status_code=422, detail=f"Scope {', '.join(repeated)} given more than once."
        )
    return dict(sorted(pairs, key=lambda pair: order.index(pair[0])))

# Scopes are parsed by hand (above), so FastAPI can't document them on its own.
scope_params_openapi = {
    "parameters": [
        {
            "name": "scope",
            "in": "query",
            "required": False,
            "schema": {"type": "array", "items": {"type": "string"}},
            "style": "form",
            "explode": True,
            "description": "Scope identifiers as `<scope>:<identifier>`, repeated, e.g. "
                           "`?scope=hostname:host1&scope=subject_id:123`. Merged in Ficus's scope "
                           "precedence (GET /v1/scopes), not in the order given. The legacy "
                           "`?hostname=host1&subject_id=123` style still works (same precedence).",
        }
    ]
}

@router.get("/{namespace}", openapi_extra=scope_params_openapi, response_model_exclude_none=True)
def get_config_endpoint(
    namespace: str,
    mode: str = DEFAULT_MODE,
    layers: bool = False,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
    data_store: DataStore = Depends(data_store),
) -> ConfigDataResponse:
    try:
        config = get_config(
            data_store,
            namespace,
            mode=mode,
            scope_identifiers=scope_identifiers,
            include_layers=layers,
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
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
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


@router.patch("/{namespace}", openapi_extra=scope_params_openapi)
def update_config_endpoint(
    data: dict,
    namespace: str,
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    scope_identifiers: dict[str, str] = Depends(_parse_scopes),
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
    """Resolve fields across identifiers of a scope.

    `fields` and `identifiers` are comma-separated; omit either to get all of them.
    """
    try:
        names = [name.strip() for name in fields.split(",") if name.strip()] if fields else None
        ids = [i.strip() for i in identifiers.split(",") if i.strip()] if identifiers else None
        return AcrossConfigResponse(
            items=resolve_across(data_store, namespace, scope, mode, names, ids)
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
