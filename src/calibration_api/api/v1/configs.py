from fastapi import APIRouter, Depends

from calibration_api.database.zookeeper.config_server import get_zk_client
from kazoo.client import KazooClient

from calibration_api.crud.zookeeper.configs import get_configs


router = APIRouter(prefix="/configs", tags=["Configs"])


@router.get("/projects/{project_name}") 
def get_project_config(project_name: str, rig_name: str | None = None, zk: KazooClient = Depends(get_zk_client)):

    data = get_configs(zk, project_name, rig_name)

    # If you want to return as plaintext yaml format, add the following: 
    #   @router.get("/projects/{project_name}", response_class=PlainTextResponse)
    #   yaml_output = yaml.dump(parsed_yaml, sort_keys=False)
    #   return PlainTextResponse(yaml_output, media_type="text/yaml")

    return {"message": "Query successful", "output": data}
