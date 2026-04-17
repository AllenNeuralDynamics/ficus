from fastapi import APIRouter, UploadFile
from fastapi import HTTPException
from pathlib import Path


from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigDecodeError,
    ConfigNotFoundError,
    ConfigSerializeError,
    PathIsDirectoryError,
    UnsupportedFileTypeError,
)
from ficus.services.configs import (
    get_config,
    get_config_no_merge,
    get_all_paths,
    get_all_files,
    save_config_obj,
    save_config_file,
    update_config_file,
    update_config_object,
    delete_config,
)
from ficus.schemas.configs import ConfigResponse, ConfigDataResponse, ConfigErrorResponse


router = APIRouter(prefix="/configs", tags=["Configs"])
BASEDIR = Path(__file__).resolve().parent.parent.parent.parent


@router.get(
    "/list_paths/{namespace}/{filename}",
    description=Path(BASEDIR / "docs/get_all_paths_with_file.md").read_text(),
)
def get_all_paths_with_file(namespace: str, filename: str) -> ConfigDataResponse:
    data = get_all_paths(namespace, filename)
    return ConfigDataResponse(
        message=f"Successfully retrieved list of paths containing {namespace}/{filename}",
        data=data,
        details={},
    )


@router.get(
    "/list_files/{namespace}",
    description=Path(BASEDIR / "docs/get_all_files_in_path.md").read_text(),
)
def get_all_files_in_path(namespace: str, hostname: str | None = None) -> ConfigDataResponse:
    data = get_all_files(namespace, hostname)
    return ConfigDataResponse(
        message=f"Successfully retrieved list of files in path defaults/{namespace} and {hostname}/{namespace}",
        data=data,
        details={},
    )


@router.get(
    "/{namespace}",
    description=Path(BASEDIR / "docs/get_configuration.md").read_text(),
    responses={404: {"model": ConfigErrorResponse, "description": "File not found"}},
)
def get_configuration(
    namespace: str,
    filename: str | None = None,
    hostname: str | None = None,
) -> ConfigDataResponse:
    try:
        config, paths = get_config(namespace=namespace, filename=filename, hostname=hostname)
        return ConfigDataResponse(
            message="Successfully retrieved configuration file",
            data=config,
            details={"files": paths},
        )
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/no-merge/{namespace}",
    description=Path(BASEDIR / "docs/get_configuration_no_merge.md").read_text(),
    responses={404: {"model": ConfigErrorResponse, "description": "File not found"}},
)
def get_configuration_no_merge(
    namespace: str,
    filename: str | None = None,
    hostname: str | None = None,
) -> ConfigDataResponse:
    try:
        config, path = get_config_no_merge(namespace=namespace, filename=filename, hostname=hostname)
        return ConfigDataResponse(
            message="Successfully retrieved single configuration file",
            data=config,
            details={"file": path},
        )
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/upload/{namespace}",
    description=Path(BASEDIR / "docs/post_configuration_file.md").read_text(),
    responses={
        400: {"model": ConfigErrorResponse, "description": "Failed to decode file - invalid format"},
        409: {"model": ConfigErrorResponse, "description": "File already exists"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
    },
)
async def post_configuration_file(namespace: str, file: UploadFile, hostname: str | None = None) -> ConfigDataResponse:
    try:
        raw = await file.read()
        filename = file.filename if file.filename else ""
        saved_data, path = save_config_file(namespace=namespace, filename=filename, data=raw, hostname=hostname)
        return ConfigDataResponse(
            message="Successfully added configuration file",
            details={"path": path},
            data=saved_data,
        )
    except ConfigDecodeError as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    except ConfigExistsError as e:
        raise HTTPException(status_code=409, detail=f"{e}")
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.post(
    "/{namespace}/{filename}",
    description=Path(BASEDIR / "docs/post_configuration.md").read_text(),
    responses={
        409: {"model": ConfigErrorResponse, "description": "File already exists"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
        500: {"model": ConfigErrorResponse, "description": "Failed to serialize configuration data"},
    },
)
def post_configuration(namespace: str, filename: str, data: dict, hostname: str | None = None) -> ConfigDataResponse:
    try:
        saved_data, path = save_config_obj(namespace=namespace, filename=filename, data=data, hostname=hostname)
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


@router.put(
    "/upload/{namespace}",
    description=Path(BASEDIR / "docs/put_configuration_file.md").read_text(),
    responses={
        400: {"model": ConfigErrorResponse, "description": "Failed to decode file - invalid format"},
        404: {"model": ConfigErrorResponse, "description": "File not found"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
    },
)
async def replace_configuration_file(
    namespace: str, filename: str, file: UploadFile, hostname: str | None = None
) -> ConfigDataResponse:
    try:
        raw = await file.read()
        saved_data, path = save_config_file(
            namespace=namespace, filename=filename, data=raw, hostname=hostname, override=True, create_if_missing=False
        )
        return ConfigDataResponse(
            message="Successfully replaced configuration file",
            details={"path": path},
            data=saved_data,
        )
    except ConfigDecodeError as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"{e}")
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.put(
    "/{namespace}/{filename}",
    description=Path(BASEDIR / "docs/put_configuration.md").read_text(),
    responses={
        404: {"model": ConfigErrorResponse, "description": "File not found"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
        500: {"model": ConfigErrorResponse, "description": "Failed to serialize configuration data"},
    },
)
def replace_configuration(namespace: str, filename: str, data: dict, hostname: str | None = None) -> ConfigDataResponse:
    try:
        saved_data, path = save_config_obj(
            namespace=namespace, filename=filename, data=data, hostname=hostname, override=True, create_if_missing=False
        )
        return ConfigDataResponse(
            message="Successfully replaced configuration file",
            details={"path": path},
            data=saved_data,
        )
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"{e}")
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=415, detail=f"{e}")
    except ConfigSerializeError as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.patch(
    "/upload/{namespace}/{filename}",
    description=Path(BASEDIR / "docs/patch_configuration_file.md").read_text(),
    responses={
        400: {"model": ConfigErrorResponse, "description": "Failed to decode file - invalid format"},
        404: {"model": ConfigErrorResponse, "description": "File not found"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
        500: {"model": ConfigErrorResponse, "description": "Failed to serialize configuration data"},
    },
)
async def update_configuration_file(
    namespace: str, filename: str, file: UploadFile, hostname: str | None = None
) -> ConfigDataResponse:
    try:
        raw = await file.read()
        partial_filename = file.filename if file.filename else ""
        saved_data, path = update_config_file(
            namespace=namespace, filename=filename, partial_filename=partial_filename, data=raw, hostname=hostname
        )
        return ConfigDataResponse(
            message="Successfully updated configuration file",
            details={"path": path},
            data=saved_data,
        )
    except ConfigDecodeError as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"{e}")
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=415, detail=f"{e}")
    except ConfigSerializeError as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router.patch(
    "/{namespace}/{filename}",
    description=Path(BASEDIR / "docs/patch_configuration.md").read_text(),
    responses={
        404: {"model": ConfigErrorResponse, "description": "File not found"},
        409: {"model": ConfigErrorResponse, "description": "File already exists"},
        415: {"model": ConfigErrorResponse, "description": "Unsupported file type"},
        500: {"model": ConfigErrorResponse, "description": "Failed to serialize configuration data"},
    },
)
async def update_configuration(
    namespace: str, filename: str, data: dict, hostname: str | None = None
) -> ConfigDataResponse:
    try:
        saved_data, path = update_config_object(namespace=namespace, filename=filename, data=data, hostname=hostname)
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


@router.delete(
    "/{namespace}/{filename}",
    description=Path(BASEDIR / "docs/delete_configuration.md").read_text(),
    responses={
        400: {"model": ConfigErrorResponse, "description": "Path is a directory and cannot be deleted"},
        404: {"model": ConfigErrorResponse, "description": "File not found"},
    },
)
def delete_configuration(namespace: str, filename: str, hostname: str | None = None) -> ConfigResponse:
    try:
        path = delete_config(namespace=namespace, filename=filename, hostname=hostname)
        return ConfigResponse(
            message="Successfully deleted configuration file",
            details={"path": path},
        )
    except PathIsDirectoryError as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    except ConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"{e}")
