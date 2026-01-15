from fastapi import APIRouter, UploadFile

from ficus.services.configs import ConfigStore
from ficus.schemas.configs import ConfigResponse, ConfigScope, DataSources


router = APIRouter(prefix="/configs", tags=["Configs"])


@router.get("/")
def get_configuration_file(
    namespace: str,
    file_name: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
    group_name: str | None = None,
    rig_name: str | None = None,
) -> ConfigResponse:
    config, paths = ConfigStore(datasource=datasource).get_config(
        namespace=namespace, file_name=file_name, group_name=group_name, rig_name=rig_name
    )
    return ConfigResponse(
        message="Successfully retrieved data",
        data=config,
        details={"source": datasource, "paths": paths},
    )


@router.post("/")
def post_configuration_data(
    data: dict,
    namespace: str,
    file_name: str,
    config_scope: ConfigScope = ConfigScope.DEFAULTS,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    ConfigStore(datasource=datasource).save_config(namespace, file_name, config_scope, data)
    return ConfigResponse(
        message="Successfully saved data",
        data={},
        details={"source": datasource, "scope": config_scope},
    )


@router.post("/uploadfile")
async def post_configuration_upload_file(
    file: UploadFile,
    namespace: str,
    config_scope: ConfigScope = ConfigScope.DEFAULTS,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    ConfigStore(datasource=datasource).save_config_file(namespace, file.filename, config_scope, await file.read())
    return ConfigResponse(
        message="Successfully saved data",
        data={},
        details={"source": datasource, "scope": config_scope},
    )
