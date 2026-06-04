import inspect
import fastapi

from fastapi import APIRouter, Body
from fastapi import HTTPException
from pathlib import Path
from typing import Annotated, Callable


from ficus.core.config import settings
from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigNotFoundError,
    ConfigSerializeError,
    PathIsDirectoryError,
    UnsupportedFileTypeError,
)
from ficus.services.configs import (
    get_config,
    save_config,
    update_config,
    delete_config,
    get_all_files,
)
from ficus.schemas.configs import ConfigResponse, ConfigDataResponse, ConfigErrorResponse


################################################################################
#
#   Utility
#
################################################################################


router = APIRouter()
BASEDIR = Path(__file__).resolve().parents[3]

WINDOWS_SAFE_PATTERN = r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$"


def _get_endpoint_info_from_scopes(endpoint_creator: Callable) -> list[tuple[str, Callable, str]]:
    """
    Generates endpoint info (path, handler, scope_name) for each scope defined in settings.
    Info is used to dynamically create endpoints for each scope (e.g. computers, subjects, etc.).
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

    for scope in settings.scopes:
        scope_name = scope.name
        identifier_name = scope.identifier_name

        path = f"/{scope_name}/{{{identifier_name}}}/namespaces/{{namespace}}/config/{{filename}}"

        handler = endpoint_creator()

        sig = inspect.signature(handler)
        # Grab all parameters except for **kwargs (omit seeing **kwargs in function signature)
        new_params = [p for p in sig.parameters.values() if p.kind != inspect.Parameter.VAR_KEYWORD]
        # Create dynamic parameter for identifier_name
        dynamic_param = inspect.Parameter(
            identifier_name,
            inspect.Parameter.KEYWORD_ONLY,
            annotation=str,
            default=fastapi.Path(..., description=f"The ID for {scope_name}"),
        )
        dynamic_param = dynamic_param.replace(
            default=fastapi.Path(
                ...,
                description=f"The ID for {scope_name}",
                pattern=WINDOWS_SAFE_PATTERN,
            )
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
    responses={404: {"model": ConfigErrorResponse, "description": "File not found"}},
)
def get_configuration(
    namespace: Annotated[
        str,
        fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN),
    ],
    filename: Annotated[
        str | None,
        fastapi.Query(pattern=WINDOWS_SAFE_PATTERN),
    ] = None,
    hostname: Annotated[
        str | None,
        fastapi.Query(pattern=WINDOWS_SAFE_PATTERN),
    ] = None,
    subject_id: Annotated[
        str | None,
        fastapi.Query(pattern=WINDOWS_SAFE_PATTERN),
    ] = None,
    merge: bool = True,
) -> ConfigDataResponse:
    try:
        identifier_names = {}
        if hostname:
            identifier_names["hostname"] = hostname
        if subject_id:
            identifier_names["subject_id"] = subject_id

        config, paths = get_config(
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


def get_create_config_handler() -> Callable:
    """
    Factory function to create handler for creating new configs.
    Contains core functionality used by all endpoints related to config creation.

    Returns:
    --------
        create_config_handler: Callable
            The actual handler function that will be used in the endpoint
    """

    async def create_config_handler(
        namespace: Annotated[
            str,
            fastapi.Path(
                ...,
                description="The namespace for the configuration file",
                pattern=WINDOWS_SAFE_PATTERN,
            ),
        ],
        filename: Annotated[
            str,
            fastapi.Path(
                ...,
                description="The name of the configuration file, including extension.",
                pattern=WINDOWS_SAFE_PATTERN,
            ),
        ],
        data: dict = Body(None, description="The configuration data."),
        **kwargs,
    ) -> ConfigDataResponse:
        try:
            saved_data, path = save_config(
                namespace=namespace, filename=filename, data=data, identifier_names=kwargs
            )
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
    responses={
        409: {"model": ConfigErrorResponse, "description": "File already exists"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
        500: {
            "model": ConfigErrorResponse,
            "description": "Failed to serialize configuration data",
        },
    },
)
async def create_defaults_config(
    namespace: Annotated[str, fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN)],
    filename: Annotated[str, fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN)],
    data: dict | None = None,
):
    handler = get_create_config_handler()
    return await handler(namespace=namespace, filename=filename, data=data)


# Grab endpoint info for each scope and create endpoints
for path, endpoint, scope_name in _get_endpoint_info_from_scopes(get_create_config_handler):
    router.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=["POST"],
        tags=[f"{scope_name}"],
        description=Path(BASEDIR / "docs/post_configuration.md").read_text(),
        responses={
            409: {"model": ConfigErrorResponse, "description": "File already exists"},
            415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
            500: {
                "model": ConfigErrorResponse,
                "description": "Failed to serialize configuration data",
            },
        },
    )


################################################################################
#
#   Update Config
#
################################################################################


def get_update_config_handler() -> Callable:
    """
    Factory function to create handler for updating configs.
    Contains core functionality used by all endpoints related to config updates.

    Returns:
    --------
        update_config_handler: Callable
            The actual handler function that will be used in the endpoint.
    """

    async def update_config_handler(
        namespace: Annotated[
            str,
            fastapi.Path(
                ...,
                description="The namespace for the configuration file",
                pattern=WINDOWS_SAFE_PATTERN,
            ),
        ],
        filename: Annotated[
            str,
            fastapi.Path(
                ...,
                description="The name of the configuration file, including extension.",
                pattern=WINDOWS_SAFE_PATTERN,
            ),
        ],
        data: dict = Body(None, description="The configuration data."),
        **kwargs,
    ) -> ConfigDataResponse:
        try:
            saved_data, path = update_config(
                namespace=namespace, filename=filename, data=data, identifier_names=kwargs
            )
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
    responses={
        404: {"model": ConfigErrorResponse, "description": "File not found"},
        409: {"model": ConfigErrorResponse, "description": "File already exists"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
        500: {
            "model": ConfigErrorResponse,
            "description": "Failed to serialize configuration data",
        },
    },
)
async def update_defaults_config(
    namespace: Annotated[str, fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN)],
    filename: Annotated[str, fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN)],
    data: dict | None = None,
):
    handler = get_update_config_handler()
    return await handler(namespace=namespace, filename=filename, data=data)


for path, endpoint, scope_name in _get_endpoint_info_from_scopes(get_update_config_handler):
    router.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=["PATCH"],
        tags=[f"{scope_name}"],
        description=Path(BASEDIR / "docs/patch_configuration.md").read_text(),
        responses={
            404: {"model": ConfigErrorResponse, "description": "File not found"},
            409: {"model": ConfigErrorResponse, "description": "File already exists"},
            415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
            500: {
                "model": ConfigErrorResponse,
                "description": "Failed to serialize configuration data",
            },
        },
    )


################################################################################
#
#   Delete Config
#
################################################################################


def get_delete_config_handler() -> Callable:
    """
    Factory function to create handler for deleting configs.
    Contains core functionality used by all endpoints related to config deletion.

    Returns:
    --------
        delete_config_handler: Callable
            The actual handler function that will be used in the endpoint.
    """

    async def delete_config_handler(
        namespace: Annotated[
            str,
            fastapi.Path(
                ...,
                description="The namespace for the configuration file",
                pattern=WINDOWS_SAFE_PATTERN,
            ),
        ],
        filename: Annotated[
            str,
            fastapi.Path(
                ...,
                description="The name of the configuration file, including extension.",
                pattern=WINDOWS_SAFE_PATTERN,
            ),
        ],
        **kwargs,
    ) -> ConfigResponse:
        try:
            path = delete_config(namespace=namespace, filename=filename, identifier_names=kwargs)
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
    namespace: Annotated[str, fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN)],
    filename: Annotated[str, fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN)],
):
    handler = get_delete_config_handler()
    return await handler(namespace=namespace, filename=filename)


for path, endpoint, scope_name in _get_endpoint_info_from_scopes(get_delete_config_handler):
    router.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=["DELETE"],
        tags=[f"{scope_name}"],
        description=Path(BASEDIR / "docs/delete_configuration.md").read_text(),
        responses={
            400: {
                "model": ConfigErrorResponse,
                "description": "Path is a directory and cannot be deleted",
            },
            404: {"model": ConfigErrorResponse, "description": "File not found"},
        },
    )


################################################################################
#
#   List configs
#
################################################################################


@router.get(
    "/list_files/{namespace}/configs",
    description=Path(BASEDIR / "docs/get_all_files_in_path.md").read_text(),
    responses={404: {"model": ConfigErrorResponse, "description": "File not found"}},
)
def get_all_files_in_path(
    namespace: Annotated[
        str,
        fastapi.Path(..., pattern=WINDOWS_SAFE_PATTERN),
    ],
    filename: Annotated[
        str | None,
        fastapi.Query(pattern=WINDOWS_SAFE_PATTERN),
    ] = None,
    hostname: Annotated[
        str | None,
        fastapi.Query(pattern=WINDOWS_SAFE_PATTERN),
    ] = None,
    subject_id: Annotated[
        str | None,
        fastapi.Query(pattern=WINDOWS_SAFE_PATTERN),
    ] = None,
) -> ConfigDataResponse:
    try:
        identifier_names = {}
        if hostname:
            identifier_names["hostname"] = hostname
        if subject_id:
            identifier_names["subject_id"] = subject_id

        data = get_all_files(namespace, identifier_names=identifier_names, filename=filename)
        message = f"Retrieved list of files in path defaults/{namespace} and scopes"

        return ConfigDataResponse(
            message=message,
            data=data,
            details={},
        )
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
