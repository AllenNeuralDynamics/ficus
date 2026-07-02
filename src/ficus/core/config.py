import json
import os
from loguru import logger
from pathlib import Path
from typing import Tuple, Type

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field, field_name):
        pass

    def __call__(self):
        path_from_env = os.getenv("FICUS_CONFIG_PATH")
        if path_from_env:
            logger.debug(f"Found FICUS config path from environment variable: "
                          f"{str(path_from_env)}")
            json_path = Path(path_from_env)
        else:
            json_path = Path(__file__).parents[3] / "data" / "ficus_setup.json"
            logger.debug(f"Falling back to default FICUS config from: "
                          f"{str(json_path)}")

        if json_path.exists():
            with open(json_path, "r") as f:
                return json.load(f)

        return {}  # should not happen.


class Settings(BaseSettings):
    """Settings for a Ficus Instance."""
    config_filename: str = "ficus_setup.json"
    # TODO: if this is ordered, then we also drive merge order from here.
    scopes: set[str] = {"hostname", "subject_id"}
    store: str = "ZKStore"
    root_dir: str = "scratch"
    host: str = "eng-logtools:2181"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Ordered by precedence
        return (
            init_settings,  # Passed in from Settings (testing overrides)
            env_settings,  # Environment variables (quick fix overrides)
            dotenv_settings,  # .env file (secrets)
            JsonConfigSettingsSource(settings_cls),  # JSON config file (main config values)
        )


settings = Settings()
