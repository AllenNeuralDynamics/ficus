from fastapi import APIRouter, UploadFile
from fastapi import HTTPException
from kazoo.exceptions import NoNodeError, NotEmptyError

from ficus.services.configs import (
    get_config,
    get_all_paths,
    get_all_files,
    save_config_obj,
    save_config_file,
    update_config_file,
    update_config_object,
    delete_config,
)
from ficus.schemas.configs import ConfigResponse, ConfigDataResponse


router = APIRouter(prefix="/configs", tags=["Configs"])


@router.get("/")
def get_configuration(
    namespace: str,
    filename: str,
    hostname: str | None = None,
    merge: bool = True,
) -> ConfigDataResponse:
    try:
        config, paths = get_config(namespace=namespace, filename=filename, hostname=hostname, merge=merge)
        return ConfigDataResponse(
            message="Successfully retrieved configuration file",
            data=config,
            details={"files": paths},
        )
    except NoNodeError:
        config = f"/computers/{hostname}{namespace}/{filename}" if hostname else f"/default/{namespace}/{filename}"
        raise HTTPException(status_code=404, detail=f"Config {config} not found")


@router.post("/")
def post_configuration(namespace: str, filename: str, data: dict, hostname: str | None = None) -> ConfigResponse:
    try:
        path = save_config_obj(namespace=namespace, filename=filename, data=data, hostname=hostname)
        return ConfigResponse(
            message="Successfully added configuration file",
            details={"path": path},
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=f"{e}")
    except ValueError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.post("/upload")
async def post_configuration_file(namespace: str, file: UploadFile, hostname: str | None = None) -> ConfigResponse:
    try:
        raw = await file.read()
        path = save_config_file(namespace=namespace, filename=file.filename, data=raw, hostname=hostname)
        return ConfigResponse(
            message="Successfully added configuration file",
            details={"path": path},
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=f"{e}")
    except ValueError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.put("/")
def replace_configuration(namespace: str, filename: str, data: dict, hostname: str | None = None) -> ConfigResponse:
    try:
        path = save_config_obj(namespace=namespace, filename=filename, data=data, hostname=hostname, override=True)
        return ConfigResponse(
            message="Successfully replaced configuration file",
            details={"path": path},
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=f"{e}")
    except ValueError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.put("/upload")
async def replace_configuration_file(namespace: str, file: UploadFile, hostname: str | None = None) -> ConfigResponse:
    try:
        raw = await file.read()
        path = save_config_file(namespace=namespace, filename=file.filename, data=raw, hostname=hostname, override=True)
        return ConfigResponse(
            message="Successfully replaced configuration file",
            details={"path": path},
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=f"{e}")
    except ValueError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.patch("/")
async def update_configuration(
    namespace: str, filename: str, data: dict, hostname: str | None = None
) -> ConfigResponse:
    try:
        path = update_config_object(namespace=namespace, filename=filename, data=data, hostname=hostname)
        return ConfigResponse(
            message="Successfully updated configuration file",
            details={"path": path},
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=f"{e}")
    except ValueError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.patch("/upload")
async def update_configuration_file(
    namespace: str, filename: str, file: UploadFile, hostname: str | None = None
) -> ConfigResponse:
    try:
        raw = await file.read()
        path = update_config_file(
            namespace=namespace, filename=filename, partial_filename=file.filename, data=raw, hostname=hostname
        )
        return ConfigResponse(
            message="Successfully updated configuration file",
            details={"path": path},
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=f"{e}")
    except ValueError as e:
        raise HTTPException(status_code=415, detail=f"{e}")


@router.delete("/")
def delete_configuration(namespace: str, filename: str, hostname: str | None = None) -> ConfigResponse:
    try:
        path = delete_config(namespace=namespace, filename=filename, hostname=hostname)
        return ConfigResponse(
            message="Successfully delete configuration file",
            details={"path": path},
        )
    except NotEmptyError as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    except NoNodeError:
        config = f"/computers/{hostname}{namespace}/{filename}" if hostname else f"/default/{namespace}/{filename}"
        raise HTTPException(status_code=404, detail=f"Config {config} not found")


@router.get("/list_paths")
def get_all_paths_with_file(namespace: str, filename: str) -> ConfigDataResponse:
    data = get_all_paths(namespace, filename)
    return ConfigDataResponse(
        message=f"Successfully retrieved list of paths containing {namespace}/{filename}",
        data=data,
        details={},
    )


@router.get("/list_files")
def get_all_files_in_path(namespace: str, hostname: str | None = None) -> ConfigDataResponse:
    data = get_all_files(namespace, hostname)
    return ConfigDataResponse(
        message=f"Successfully retrieved list of files in path defaults/{namespace} and {hostname}/{namespace}",
        data=data,
        details={},
    )
