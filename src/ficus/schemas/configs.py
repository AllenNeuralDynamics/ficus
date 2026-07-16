from pathlib import Path
from typing import Any, TypeAlias

from pydantic import BaseModel


class ConfigResponse(BaseModel):
    message: str
    details: dict


class ConfigDataResponse(ConfigResponse):
    data: dict | list


ConfigData: TypeAlias = dict[str, Any]


class ConfigErrorResponse(BaseModel):
    details: str


class ConfigObject(BaseModel):
    data: ConfigData
    namespace: str
    mode: str
    scope_identifiers: dict[str, str]
    override_stack: list[Path]
    # components: list[Leaf] # TODO: switch override stack to list[Leaf]

# class Leaf(BaseModel):
#     content: str
#     suffix: str
#     namespace: str
#     mode: str
#     scope: str | None
#     scope_identifier: str | None
