from enum import Enum
from pydantic import BaseModel
from typing import Any, TypeAlias


class DataSources(str, Enum):
    ZOOKEEPER = "zookeeper"
    GITHUB = "github"
    POSTGRESQL = "postgresql"


class ConfigInput(BaseModel):
    namespace: str
    file_name: str
    group_name: str | None = None
    rig_name: str | None = None


class ConfigResponse(BaseModel): 
    message: str
    data: Any
    details: dict


ConfigData: TypeAlias = dict[str, Any]