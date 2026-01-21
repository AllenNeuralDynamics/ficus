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
    """Get merged configuration file for a given namespace, file name, datasource, and optional group/rig names. The
    priority order for merging is defaults < groups < rigs. If group_name and rig_name are not provided, only the
    defaults file is returned."""
    config, paths = ConfigStore(datasource=datasource).get_config(
        namespace=namespace, file_name=file_name, group_name=group_name, rig_name=rig_name
    )
    return ConfigResponse(
        message="Successfully merged configuration file",
        data=config,
        details={"source": datasource, "paths": paths},
    )


@router.get("/list_files")
def get_all_configuration_files(
    namespace: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    """List all configuration files for each scope (defaults, groups, rigs), given namespace and datasource. No merging
    is performed on these full/partial files"""
    files = ConfigStore(datasource=datasource).get_list_of_all_configs(namespace=namespace)
    return ConfigResponse(
        message="Successfully retrieved configuration files in each scope",
        data=files,
        details={"source": datasource},
    )


@router.post("/defaults")
def post_configuration_data_defaults(
    data: dict,
    namespace: str,
    file_name: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    """Save an object as a config file in the defaults scope. Will attempt to save as yaml or json based on file
    extension."""
    ConfigStore(datasource=datasource).save_config(namespace, file_name, ConfigScope.DEFAULTS, data)
    return ConfigResponse(message="Successfully saved data into defaults scope", data={}, details={})


@router.post("/groups")
def post_configuration_data_groups(
    data: dict,
    namespace: str,
    file_name: str,
    group_name: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    """Save an object as a config file in the groups scope. Will attempt to save as yaml or json based on file
    extension."""
    ConfigStore(datasource=datasource).save_config(namespace, file_name, ConfigScope.GROUPS, data, group_name)
    return ConfigResponse(message="Successfully saved into groups scope", data={}, details={})


@router.post("/rigs")
def post_configuration_data_rigs(
    data: dict,
    namespace: str,
    file_name: str,
    rig_name: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    """Save an object as a config file in the rigs scope. Will attempt to save as yaml or json based on file
    extension."""
    ConfigStore(datasource=datasource).save_config(namespace, file_name, ConfigScope.RIGS, data, rig_name)
    return ConfigResponse(message="Successfully saved data into rigs scope", data={}, details={})


@router.post("/defaults/uploadfile")
async def post_configuration_upload_file_defaults(
    file: UploadFile,
    namespace: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    """Upload a file to be saved in the defaults scope. The file content is read as bytes and saved directly."""
    ConfigStore(datasource=datasource).save_config_file(
        namespace, file.filename, ConfigScope.DEFAULTS, await file.read()
    )
    return ConfigResponse(
        message="Successfully saved file in defaults scope",
        data={},
        details={},
    )


@router.post("/groups/uploadfile")
async def post_configuration_upload_file_groups(
    file: UploadFile,
    namespace: str,
    group_name: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    """Upload a file to be saved in the groups scope. The file content is read as bytes and saved directly."""
    ConfigStore(datasource=datasource).save_config_file(
        namespace, file.filename, ConfigScope.GROUPS, await file.read(), group_name
    )
    return ConfigResponse(
        message="Successfully saved file in groups scope",
        data={},
        details={},
    )


@router.post("/rigs/uploadfile")
async def post_configuration_upload_file_rigs(
    file: UploadFile,
    namespace: str,
    rig_name: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
) -> ConfigResponse:
    """Upload a file to be saved in the rigs scope. The file content is read as bytes and saved directly."""
    ConfigStore(datasource=datasource).save_config_file(
        namespace, file.filename, ConfigScope.RIGS, await file.read(), rig_name
    )
    return ConfigResponse(
        message="Successfully saved file in rigs scope",
        data={},
        details={},
    )
