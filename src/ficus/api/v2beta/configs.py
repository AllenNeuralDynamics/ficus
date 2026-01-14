from fastapi import APIRouter


from ficus.services.configs import ConfigStore
from ficus.schemas.configs import ConfigInput, ConfigResponse, DataSources


router = APIRouter(prefix="/configs", tags=["Configs"])


@router.get("/")
def get_configuration_file(
    namespace: str,
    file_name: str,
    datasource: DataSources = DataSources.ZOOKEEPER,
    group_name: str | None = None,
    rig_name: str | None = None,
) -> ConfigResponse:
    config_input = ConfigInput(namespace=namespace, file_name=file_name, group_name=group_name, rig_name=rig_name)
    config, paths = ConfigStore(datasource=datasource).get_configs(config_input)
    return ConfigResponse(
        message="Successfully retrieved data",
        data=config,
        details={"source": datasource, "paths": paths},
    )


# TODO: Create write endpoint (object input)
@router.post("/")
def post_configuration_file(config_input): ...


# TODO: Create write endpoint (file input)
