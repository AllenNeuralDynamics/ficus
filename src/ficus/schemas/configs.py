from pathlib import Path
from typing import Any, TypeAlias

from pydantic import BaseModel


class ConfigResponse(BaseModel):
    message: str


class ConfigDataResponse(ConfigResponse):
    config: "ConfigObject"


ConfigData: TypeAlias = dict[str, Any]


class ConfigErrorResponse(BaseModel):
    details: str


class ConfigObject(BaseModel):
    data: ConfigData
    namespace: str
    mode: str
    scope_identifiers: dict[str, str]
    override_stack: list[Path]
    layers: list["ConfigLayer"] | None = None
    # components: list[Leaf] # TODO: switch override stack to list[Leaf]


class ConfigLayer(BaseModel):
    path: Path
    data: ConfigData


class AcrossConfigItem(BaseModel):
    identifier: str
    values: ConfigData
    sources: dict[str, str | None]


class AcrossConfigResponse(BaseModel):
    items: list[AcrossConfigItem]

# class Leaf(BaseModel):
#     content: str
#     suffix: str
#     namespace: str
#     mode: str
#     scope: str | None
#     scope_identifier: str | None
