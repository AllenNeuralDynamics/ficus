from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from ficus.database.zookeeper.config_server import get_zk_client
from kazoo.client import KazooClient

from ficus.crud.zookeeper.configs import get_configs


router = APIRouter(prefix="/configs", tags=["Configs"])


@router.get("/projects/{project_name}") 
def get_project_config(project_name: str, rig_name: str | None = None, zk: KazooClient = Depends(get_zk_client)):
    data = get_configs(zk, project_name, rig_name)

    if isinstance(data, dict):
        return data
    else:
        return PlainTextResponse(data)
