import json

from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScopeSchema(BaseModel):
    name: str
    description: str


class Settings(BaseSettings):
    config_filename: str = "ficus_setup.json"
    zk_host: str = "eng-logtools:2181"
    zk_root_node: str = "scratch"
    scopes: list[ScopeSchema] = []

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_data_from_json()

    def load_data_from_json(self):
        json_path = Path(__file__).parent.parent.parent.parent / "data" / self.config_filename
        if json_path.exists():
            with open(json_path, "r") as f:
                data = json.load(f)
                self.scopes = [ScopeSchema(**s) for s in data.get("scopes", [])]
                self.zk_root_node = data.get("zk_root_node", self.zk_root_node)


settings = Settings()
