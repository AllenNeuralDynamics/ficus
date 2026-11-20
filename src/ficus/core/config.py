import json
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for a Ficus Instance: environment variables, then ``.env``, then these defaults.

    ``GET /v1/settings`` returns these, so a secret added here must be a ``SecretStr``
    (it is shown as ``**********``).
    """
    # Scope precedence, lowest first: configs merge defaults, then these in this order.
    scopes: list[str] = ["hostname", "subject_id"]
    store: Literal["zookeeper", "file_system"] = "zookeeper"
    root_dir: str = "scratch"
    # ZooKeeper ensemble: a JSON list or comma-separated ``host:port`` (``ZK_HOSTS``).
    # ``ZK_HOST`` is the older name.
    zk_hosts: Annotated[list[str], NoDecode] = Field(
        default=["eng-logtools:2181"],
        validation_alias=AliasChoices("zk_hosts", "zk_host"),
    )
    # Seconds to wait for a ZooKeeper connection before a request fails.
    zk_timeout: float = Field(default=15.0, gt=0)
    # Path prefix the API is served under (``ROOT_PATH``; ``API_NAME`` is the older name). Leave it
    # empty behind a proxy that strips the prefix and sends ``X-Forwarded-Prefix`` (Traefik's
    # stripprefix does), so one image works under any prefix.
    root_path: str = Field(default="", validation_alias=AliasChoices("root_path", "api_name"))
    log_level: Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("scopes", mode="after")
    def validate_scopes(cls, v):
        if "mode" in v:
            raise ValueError("'mode' cannot be a Scope.")
        if len(set(v)) != len(v):
            raise ValueError(f"Scopes must be unique: {v}")
        return v

    @field_validator("zk_hosts", mode="before")
    @classmethod
    def split_zk_hosts(cls, v):
        if isinstance(v, str):
            v = json.loads(v) if v.lstrip().startswith("[") else v.split(",")
        return [host.strip() for host in v if host.strip()] if isinstance(v, list) else v

    @field_validator("root_path", mode="after")
    @classmethod
    def normalize_root_path(cls, v):
        v = v.strip().strip("/")
        return f"/{v}" if v else ""

    @field_validator("log_level", mode="before")
    @classmethod
    def upper_log_level(cls, v):
        return v.upper() if isinstance(v, str) else v


settings = Settings()
