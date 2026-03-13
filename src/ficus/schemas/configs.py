from pydantic import BaseModel
from typing import Any, TypeAlias


class ConfigResponse(BaseModel):
    message: str
    details: dict


class ConfigDataResponse(ConfigResponse):
    data: dict


ConfigData: TypeAlias = dict[str, Any]
