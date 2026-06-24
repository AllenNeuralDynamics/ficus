import inspect
import fastapi

from fastapi import APIRouter, Body, Request
from fastapi import HTTPException
from pathlib import Path
from typing import Callable


from ficus.core.config import settings
from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigNotFoundError,
    ConfigSerializeError,
    PathIsDirectoryError,
    UnsupportedFileTypeError,
)
from ficus.database.data_store import DataStore
from ficus.services.configs import (
    get_config,
    save_config,
    update_config,
    delete_config,
    list_all_filenames,
)
from ficus.schemas.configs import ConfigResponse, ConfigDataResponse, ConfigErrorResponse

config_error_responses = {
    400: {"model": ConfigErrorResponse, "description": "Path is a directory and "
                                                       "cannot be deleted"},
    404: {"model": ConfigErrorResponse, "description": "File not found"},
    409: {"model": ConfigErrorResponse, "description": "File already exists"},
    415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
    500: {
        "model": ConfigErrorResponse,
        "description": "Failed to serialize configuration data",}
}

def get_config_error_responses(*responses) -> dict[int | str, dict[str, ConfigErrorResponse | str]]:
    return {k: config_error_responses[k] for k in responses}


################################################################################
#
#   Utility
#
################################################################################


router = APIRouter()
BASEDIR = Path(__file__).resolve().parents[3]


def _get_endpoint_info_from_scopes(endpoint_creator: Callable) -> list[tuple[str, Callable, str]]:
    """
    Generates endpoint info (path, handler, scope_name) for each scope defined in settings.
    Info is used to dynamically create endpoints for each scope (e.g. hostname, subject_id, etc.).
    This function also dynamically injects appropriate identifier names to the function signature to
    ensure the swagger UI docs generate correctly.

    Parameters:
    -----------
    endpoint_creator : Callable
        A function that creates the endpoint handler.

    Returns:
    --------
    endpoint_data : list[tuple[str, Callable, str]]
        List of tuples containing (endpoint path, handler, scope_name)
    """
    handlers = []

    for scope_name in settings.scopes:

        path = f"/{{{scope_name}}}/namespaces/{{namespace}}/config/{{filename}}"

        handler = endpoint_creator()

        sig = inspect.signature(handler)
        # Grab all parameters except for **kwargs (omit seeing **kwargs in function signature)
        new_params = [p for p in sig.parameters.values() if p.kind != inspect.Parameter.VAR_KEYWORD]
        # Create dynamic parameter for identifier_name
        dynamic_param = inspect.Parameter(
            scope_name,
            inspect.Parameter.KEYWORD_ONLY,
            annotation=str,
            default=fastapi.Path(..., description=f"The ID for {scope_name}"),
        )
        # Insert the dynamic parameter
        new_params.append(dynamic_param)
        # Update the function signature
        handler.__signature__ = sig.replace(parameters=new_params)

        handlers.append((path, handler, scope_name))
    return handlers


################################################################################
#
#   Get Config
#
################################################################################


@router.get(
    "/namespaces/{namespace}/config",
    description=Path(BASEDIR / "docs/get_configuration.md").read_text(),
    responses=get_config_error_responses(404),
)
def get_configuration(
    request: Request,
    namespace: str,
    filename: str | None = None,
    hostname: str | None = None,
    subject_id: str | None = None,
    merge: bool = True,
) -> ConfigDataResponse:
    try:
        identifier_names = {}
        if hostname:
            identifier_names["hostname"] = hostname
        if subject_id:
            identifier_names["subject_id"] = subject_id

        config, paths = get_config(
            data_store=request.app.state.data_store,
            namespace=namespace, filename=filename, identifier_names=identifier_names, merge=merge
        )
        return ConfigDataResponse(
            message="Successfully retrieved configuration file",
            data=config,
            details={"files": paths},
        )
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


################################################################################
#
#   Create Config
#
################################################################################


def get_create_config_handler(data_store: DataStore) -> Callable:
    """
    Factory function to create handler for creating new configs.
    Contains core functionality used by all endpoints related to config creation.

    Returns:
    --------
        create_config_handler: Callable
            The actual handler function that will be used in the endpoint
    """

    async def create_config_handler(
        namespace: str = fastapi.Path(..., description="The namespace for the configuration file"),
        filename: str = fastapi.Path(
            ..., description="The name of the configuration file, including extension."
        ),
        data: dict = Body(None, description="The configuration data."),
        **kwargs,
    ) -> ConfigDataResponse:
        try:
            saved_data, path = save_config(data_store=data_store,
                                           namespace=namespace,
                                           filename=filename,
                                           data=data,
                                           scope_identifiers=kwargs)
            return ConfigDataResponse(
                message="Successfully added configuration file",
                details={"path": path},
                data=saved_data,
            )
        except ConfigExistsError as e:
            raise HTTPException(status_code=409, detail=f"{e}")
        except UnsupportedFileTypeError as e:
            raise HTTPException(status_code=415, detail=f"{e}")
        except ConfigSerializeError as e:
            raise HTTPException(status_code=500, detail=f"{e}")

    return create_config_handler


@router.post(
    "/namespaces/{namespace}/config/{filename}",
    description=Path(BASEDIR / "docs/post_configuration.md").read_text(),
    responses=get_config_error_responses(409, 415, 400),
)
async def create_defaults_config(
    request: Request,
    namespace: str,
    filename: str,
    data: dict | None = None,
):
    handler = get_create_config_handler(data_store=request.app.state.data_store)
    return await handler(namespace=namespace, filename=filename, data=data)


# Grab endpoint info for each scope and create endpoints
for path, endpoint, scope_name in _get_endpoint_info_from_scopes(get_create_config_handler):
    router.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=["POST"],
        tags=[f"{scope_name}"],
        description=Path(BASEDIR / "docs/post_configuration.md").read_text(),
        responses=get_config_error_responses(409, 415, 500)
    )


################################################################################
#
#   Update Config
#
################################################################################


def get_update_config_handler(data_store: DataStore) -> Callable:
    """
    Factory function to create handler for updating configs.
    Contains core functionality used by all endpoints related to config updates.

    Returns:
    --------
        update_config_handler: Callable
            The actual handler function that will be used in the endpoint.
    """

    async def update_config_handler(
        namespace: str = fastapi.Path(..., description="The namespace for the configuration file"),
        filename: str = fastapi.Path(
            ..., description="The name of the configuration file, including extension."
        ),
        data: dict = Body(None, description="The configuration data."),
        **kwargs,
    ) -> ConfigDataResponse:
        try:
            saved_data, path = update_config(data_store=data_store,
                                             namespace=namespace,
                                             filename=filename,
                                             data=data,
                                             scope_identifiers=kwargs)
            return ConfigDataResponse(
                message="Successfully updated configuration file",
                details={"path": path},
                data=saved_data,
            )
        except ConfigNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"{e}")
        except ConfigExistsError as e:
            raise HTTPException(status_code=409, detail=f"{e}")
        except UnsupportedFileTypeError as e:
            raise HTTPException(status_code=415, detail=f"{e}")
        except ConfigSerializeError as e:
            raise HTTPException(status_code=500, detail=f"{e}")

    return update_config_handler


@router.patch(
    "/namespaces/{namespace}/config/{filename}",
    description=Path(BASEDIR / "docs/patch_configuration.md").read_text(),
    responses=get_config_error_responses(404, 409, 415, 500)
)
async def update_defaults_config(
    request: Request,
    namespace: str,
    filename: str,
    data: dict | None = None,
):
    handler = get_update_config_handler(data_store=request.app.state.data_store)
    return await handler(namespace=namespace, filename=filename, data=data)


for path, endpoint, scope_name in _get_endpoint_info_from_scopes(get_update_config_handler):
    router.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=["PATCH"],
        tags=[f"{scope_name}"],
        description=Path(BASEDIR / "docs/patch_configuration.md").read_text(),
        responses=get_config_error_responses(404, 409, 415, 500)
    )


################################################################################
#
#   Delete Config
#
################################################################################


def get_delete_config_handler(data_store: DataStore) -> Callable:
    """
    Factory function to create handler for deleting configs.
    Contains core functionality used by all endpoints related to config deletion.

    Returns:
    --------
        delete_config_handler: Callable
            The actual handler function that will be used in the endpoint.
    """

    async def delete_config_handler(
        namespace: str = fastapi.Path(..., description="The namespace for the configuration file"),
        filename: str = fastapi.Path(
            ..., description="The name of the configuration file, including extension."
        ),
        **kwargs,
    ) -> ConfigResponse:
        try:
            path = delete_config(data_store=data_store,
                                 namespace=namespace,
                                 filename=filename,
                                 identifier_names=kwargs)
            return ConfigResponse(
                message="Successfully deleted configuration file",
                details={"path": path},
            )
        except PathIsDirectoryError as e:
            raise HTTPException(status_code=400, detail=f"{e}")
        except ConfigNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"{e}")

    return delete_config_handler


@router.delete(
    "/namespaces/{namespace}/config/{filename}",
    description=Path(BASEDIR / "docs/delete_configuration.md").read_text(),
    responses={
        400: {
            "model": ConfigErrorResponse,
            "description": "Path is a directory and cannot be deleted",
        },
        404: {"model": ConfigErrorResponse, "description": "File not found"},
    },
)
async def delete_defaults_config(
    request: Request,
    namespace: str,
    filename: str,
):
    handler = get_delete_config_handler(data_store=request.app.state.data_store)
    return await handler(namespace=namespace, filename=filename)


for path, endpoint, scope_name in _get_endpoint_info_from_scopes(get_delete_config_handler):
    router.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=["DELETE"],
        tags=[f"{scope_name}"],
        description=Path(BASEDIR / "docs/delete_configuration.md").read_text(),
        responses=get_config_error_responses(400, 404)
    )


################################################################################
#
#   List configs
#
################################################################################


@router.get(
    "/list_files/{namespace}/configs",
    description=Path(BASEDIR / "docs/get_all_files_in_path.md").read_text(),
    responses=get_config_error_responses(404)
)
def get_all_files_in_path(
    request: Request,
    namespace: str,
    hostname: str | None = None,
    subject_id: str | None = None,
) -> ConfigDataResponse:
    try:
        # FIXME: maybe just accept the dict of scope identifiers?
        scope_identifiers = {}
        if hostname:
            scope_identifiers["hostname"] = hostname
        if subject_id:
            scope_identifiers["subject_id"] = subject_id

        data = list_all_filenames(data_store=request.app.state.data_store,
                                  namespace=namespace,
                                  scope_identifiers=scope_identifiers)
        message = f"Retrieved list of files in path defaults/{namespace} and scopes"

        return ConfigDataResponse(
            message=message,
            data=data,
            details={},
        )
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
