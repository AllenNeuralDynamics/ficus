import json
import yaml

from loguru import logger
from typing import Protocol, runtime_checkable

from ficus.crud.zookeeper.configs import get_node, add_node
from ficus.database.zookeeper.config_server import get_zk_client
from ficus.schemas.configs import ConfigData, DataSources, ConfigScope


@runtime_checkable
class ConfigStrategy(Protocol):
    def get_config(self, *args, **kwargs): ...
    def save_config(self, *args, **kwargs): ...


class BaseConfigStrategy:
    def _merge_configs(self, dict_prime, dict_mod):
        """Merge two configuration dictionaries, dict_mod has higher precedence (will overwrite)"""
        for key, value in dict_mod.items():
            if isinstance(value, dict):
                if key not in dict_prime:
                    dict_prime[key] = type(value)()  # For subclasses of dict
                self._merge_configs(dict_prime[key], dict_mod[key])
            else:
                dict_prime[key] = value
        return dict_prime

    def _validate_content(self, file_name: str, data: bytes):
        """Validate file (bytes) is either a valid YAML or JSON based on content"""
        try:
            if file_name.endswith((".yml", ".yaml")):
                yaml.safe_load(data)
            elif file_name.endswith(".json"):
                json.loads(data)
            else:
                # If no extension match, allow raw text
                logger.warning(f"File extension of '{file_name}' not recognized, skipping content validation.")
                pass
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Content of '{file_name}' is not valid: {e}")


class ZookeeperConfigStrategy(BaseConfigStrategy):
    def get_config(self, namespace: str, file_name: str, group_name: str, rig_name: str) -> tuple[ConfigData, dict]:
        DEFAULT_PATH = f"/testing/defaults/{namespace}/{file_name}"
        GROUP_PATH = f"/testing/groups/{group_name}/{namespace}/{file_name}"
        RIG_PATH = f"/testing/rigs/{rig_name}/{namespace}/{file_name}"

        valid_paths = {}

        with get_zk_client() as client:
            config = get_node(client, DEFAULT_PATH) or {}
            if config:
                valid_paths["default"] = DEFAULT_PATH
            if group_name:
                group_config = get_node(client, GROUP_PATH)
                if group_config:
                    valid_paths["group"] = GROUP_PATH
                    config = self._merge_configs(config, group_config)
            if rig_name:
                rig_name = get_node(client, RIG_PATH)
                if rig_name:
                    valid_paths["rig"] = RIG_PATH
                    config = self._merge_configs(config, rig_name)

            return config, valid_paths

    def save_config(self, namespace: str, file_name: str, config_scope: ConfigScope, data):
        namespace_path = f"/testing/{config_scope.value}/{namespace}"
        file_path = f"/testing/{config_scope.value}/{namespace}/{file_name}"

        # If it's a dict/list, serialize to the format suggested by the file name
        if not isinstance(data, (bytes, str)):
            if file_name.endswith((".json")):
                data = json.dumps(data).encode("utf-8")
            else:
                # Default to YAML
                data = yaml.dump(data).encode("utf-8")
                if not file_name.endswith((".yml", ".yaml")):
                    logger.warning(f"File extension of '{file_name}' not recognized, defaulting to YAML format.")
        elif isinstance(data, str):
            data = data.encode("utf-8")

        with get_zk_client() as client:
            add_node(client, namespace_path)  # Add namespace node if not exists (no data)
            add_node(client, file_path, data)  # Add file node with data

    def save_config_file(self, namespace: str, file_name: str, config_scope: ConfigScope, data: bytes):
        self._validate_content(file_name, data)
        self.save_config(namespace, file_name, config_scope, data)


class GithubConfigStrategy(BaseConfigStrategy):
    def get_config(self):
        print("get github config")

    def save_config(self, data: dict):
        print("save github config")


class PostgresConfigStrategy(BaseConfigStrategy):
    def get_config(self):
        print("get postgres config")

    def save_config(self, data: dict):
        print("save postgres config")


class ConfigStore:
    def __init__(self, datasource: DataSources):
        self.datasource = datasource
        self.strategy = self._get_strategy_from_datasource()

    def _get_strategy_from_datasource(self) -> ConfigStrategy:
        if self.datasource == DataSources.ZOOKEEPER:
            return ZookeeperConfigStrategy()
        elif self.datasource == DataSources.GITHUB:
            return GithubConfigStrategy()
        elif self.datasource == DataSources.POSTGRESQL:
            return PostgresConfigStrategy()
        else:
            logger.error(f"Unsupported datasource: '{self.datasource}' falling back to Zookeeper as default.")
            return ZookeeperConfigStrategy()  # Default strategy

    def __getattr__(self, name):
        return getattr(self.strategy, name)
