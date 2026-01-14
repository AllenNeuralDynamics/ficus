from abc import ABC, abstractmethod
from loguru import logger

from ficus.crud.zookeeper.configs import get_configs as get_configs_zk
from ficus.database.zookeeper.config_server import get_zk_client
from ficus.schemas.configs import ConfigData, ConfigInput, DataSources


class BaseConfigStrategy(ABC):
    @abstractmethod
    def get_configs(self) -> tuple[ConfigData, dict]:
        pass

    @abstractmethod
    def save_configs(self, data: dict):
        pass

    def _merge_configs(self, dict_prime, dict_mod):
        for key, value in dict_mod.items():
            if isinstance(value, dict):
                if key not in dict_prime:
                    dict_prime[key] = type(value)()  # For subclasses of dict
                self._merge_configs(dict_prime[key], dict_mod[key])
            else:
                dict_prime[key] = value
        return dict_prime


class ZookeeperConfigStrategy(BaseConfigStrategy):
    def get_configs(self, inputs: ConfigInput) -> tuple[ConfigData, dict]:
        DEFAULT_PATH = f"/testing/defaults/{inputs.namespace}/{inputs.file_name}"
        GROUP_PATH = f"/testing/groups/{inputs.group_name}/{inputs.namespace}/{inputs.file_name}"
        RIG_PATH = f"/testing/rigs/{inputs.rig_name}/{inputs.namespace}/{inputs.file_name}"

        valid_paths = {}

        with get_zk_client() as client:
            config = get_configs_zk(client, DEFAULT_PATH) or {}
            if config:
                valid_paths["default"] = DEFAULT_PATH
            if inputs.group_name:
                group_config = get_configs_zk(client, GROUP_PATH)
                if group_config:
                    valid_paths["group"] = GROUP_PATH
                    config = self._merge_configs(config, group_config)
            if inputs.rig_name:
                inputs.rig_name = get_configs_zk(client, RIG_PATH)
                if inputs.rig_name:
                    valid_paths["rig"] = RIG_PATH
                    config = self._merge_configs(config, inputs.rig_name)

            return config, valid_paths

    def save_configs(self, data: dict):
        print("save zookeeper config")


class GithubConfigStrategy(BaseConfigStrategy):
    def get_configs(self):
        print("get github config")

    def save_configs(self, data: dict):
        print("save github config")


class PostgresConfigStrategy(BaseConfigStrategy):
    def get_configs(self):
        print("get postgres config")

    def save_configs(self, data: dict):
        print("save postgres config")


class ConfigStore:
    def __init__(self, datasource: DataSources):
        self.datasource = datasource
        self.strategy = self._get_strategy_from_datasource()

    def _get_strategy_from_datasource(self) -> BaseConfigStrategy:
        if self.datasource == DataSources.ZOOKEEPER:
            return ZookeeperConfigStrategy()
        elif self.datasource == DataSources.GITHUB:
            return GithubConfigStrategy()
        elif self.datasource == DataSources.POSTGRESQL:
            return PostgresConfigStrategy()
        else:
            logger.error(f"Unsupported datasource: '{self.datasource}' falling back to Zookeeper as default.")
            return ZookeeperConfigStrategy()  # Default strategy

    def get_configs(self, inputs: ConfigInput) -> tuple[ConfigData, dict]:
        return self.strategy.get_configs(inputs)

    def save_configs(self, data: dict = None):
        return self.strategy.save_configs(data)
