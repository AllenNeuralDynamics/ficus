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


class DryRunChange(BaseModel):
    path: str
    before: ConfigData | None
    after: ConfigData | None


class DryRunResponse(BaseModel):
    changes: list[DryRunChange]


class ConfigObject(BaseModel):
    data: ConfigData
    namespace: str
    mode: str
    scope_identifiers: dict[str, str]
    override_stack: list[Path]
    leaves: list["Leaf"] | None = None


class LeafRef(BaseModel):
    """Identifies one leaf (one config file) in the store."""

    namespace: str
    scope: str | None  # None for the defaults leaf
    scope_identifier: str | None
    mode: str
    suffix: str


class Leaf(LeafRef):
    """A leaf plus its parsed contents."""

    data: ConfigData


class AcrossConfigItem(BaseModel):
    identifier: str
    values: ConfigData
    sources: dict[str, str | None]


class AcrossConfigResponse(BaseModel):
    items: list[AcrossConfigItem]
