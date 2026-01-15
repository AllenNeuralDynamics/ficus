from enum import Enum
from pydantic import BaseModel
from typing import Any, TypeAlias


class ConfigScope(str, Enum):
    DEFAULTS = "defaults"
    GROUPS = "groups"
    RIGS = "rigs"


class DataSources(str, Enum):
    ZOOKEEPER = "zookeeper"
    GITHUB = "github"
    POSTGRESQL = "postgresql"


class ConfigResponse(BaseModel):
    message: str
    data: Any
    details: dict


ConfigData: TypeAlias = dict[str, Any]
