"""
A small module to specifically get MPE Configurations form our zookeeper quorum.
It supports local configurations and default configurations in the cases where zookeeper is not available.
"""

import copy
import datetime
import logging
import logging.config
import logging.handlers
import os
import platform
import shutil
from collections import namedtuple
from enum import Enum, auto
from hashlib import md5
from typing import Literal

import yaml
from yaml import loader
from yaml.parser import ParserError
from kazoo.client import KazooClient
from kazoo.handlers.threading import KazooTimeoutError


# from .config_server import ConfigServer

# from .log import WebHandler, setup_logging, default_logging_dict  # noqa  for backwards compatiblity

resource_path = f"{os.path.dirname(__file__)}/resources"

default_config_dict = """
linux_install_paths:
    install: ~/.config/AIBS_MPE
    local_config: config
    local_log_config: logs
    python: /opt/mcpython3
services:
    log_server: eng-logtools.corp.alleninstitute.org:9000
    python_index: http://eng-logtools.corp.alleninstitute.org:3141/aibs/dev
    zookeeper: eng-logtools.corp.alleninstitute.org:2181
windows_install_paths:
    install: /ProgramData/AIBS_MPE
    local_config: config
    local_log_config: logs
    python: /mcpython3
"""


class SerializationTypes(Enum):
    YAML = (auto(),)
    JSON = (auto(),)
    XML = (auto(),)
    PLAINTEXT = (auto(),)
    PROTOBUF = (auto(),)
    INI = auto()


class ConfigServer(KazooClient):
    """
    A dictionary and context API wrapper around the zookeeper interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        if self.exists(key):
            return self.get(key)[0]
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        self.ensure_path(key)
        self.set(key, value)

    def __delitem__(self, key):
        if self.exists(key):
            self.delete(key)

    def __enter__(self):
        try:
            self.start()
        except:
            pass

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.stop()


def source_configuration(
    project_name: str,
    hosts: str = "eng-logtools:2181",
    use_local_config: bool = False,
    send_start_log: bool = True,
    # fetch_logging_config: bool = True,
    # fetch_project_config: bool = True,
    config_type: Literal["configuration", "logging_v2"] = "configuration",
    version: str = None,
    rig_id: str = None,
    comp_id: str = None,
    serialization: str = "yaml",
    always_pass_exc_info=False,
):
    """
    Connects to the quorum and searches for the following paths:
    /mpe_defaults/[configuration | logging]
    /[projects | hardware]/<project_name>/defaults/[configuration | logging]
    /rigs/<rig_id>/[projects | hardware]/[configuration | logging]
    /rigs/<rig_id>

    :param fetch_project_config: set to False if you do not want to source a project configuration
    :param fetch_logging_config: set to False if you do not want to source a logging configuration
    :param project_name: The name of the configuration, usually project name, you want to find
    :param use_local_config: whether to use the local cache [default = True]
    :param hosts: The quorum to connect to
    :param send_start_log: Whether to send a log to the webserver (not desirable for libraries) [default = True]
    :param version: Current software version.  Can be specified but will be auto-detected if None
    :param rig_id: override for rig_id
    :param comp_id: override for comp_id
    :param serialization: the format for the document in zookeeper ['yaml', 'ini', 'json', 'xml']
    :param always_pass_exc_info: whether to always check for exc_info
    :raises: KeyError if it can't find the default configuration
    :return:
    """

    # if use_local_config:
    #     return build_local_configuration(
    #         project_name, fetch_logging_config, fetch_project_config, send_start_log, version, serialization
    #     )

    with ConfigServer(hosts=hosts, randomize_hosts=False) as zk:
        """
        Connection to the Zookeeper Server
        """

        if not version:
            version = "unknown"

        # if not zk.connected:
        #     print("Looking for local configurations ...")
        #     return build_local_configuration(project_name, fetch_logging_config, fetch_project_config, send_start_log)

        # mpe_defaults = fetch_configuration(zk, f"/mpe_defaults/configuration", required=True)
        # local_log_path, local_config_path = get_platform_paths(mpe_defaults, project_name)
        config = None

        config = compile_remote_configuration(
            zk, project_name, config_type, rig_id=rig_id, comp_id=comp_id, serialization=serialization
        )

        # if fetch_project_config:
        #     config = compile_remote_configuration(
        #         zk, project_name, "configuration", rig_id=rig_id, comp_id=comp_id, serialization=serialization
        #     )
        #     # local_log_path, local_config_path = get_platform_paths(project_config, project_name)
        #     # os.makedirs(os.path.dirname(local_config_path), exist_ok=True)
        #     # cache_remote_config(project_config, local_config_path)

        # # elif config_type == "Logging":
        # if fetch_logging_config:
        #     config = compile_remote_configuration(zk, project_name, "logging_v2", rig_id=rig_id, comp_id=comp_id)
        #     # setup_logging(project_name, os.path.expandvars(local_log_path), log_config, send_start_log, version=version,
        #     #               rig_id=rig_id,
        #     #               comp_id=comp_id,
        #     #               always_pass_exc_info=always_pass_exc_info)
        #     # cache_remote_config(log_config, local_log_path)

        if config is None:
            raise ConnectionError("Error retrieving configuration from zookeeper.")

        return config


# def build_local_configuration(
#     project_name, fetch_logging_config=True, fetch_project_config=True, send_start_log=True, version=None,
#     serialization="yaml"  # noqa
# ):
#     """
#     Builds logging and project configuration from local files and mpeconfig defaults as necessary.  This can be useful
#     for one-off configurations for testing when you don't want to edit the zookeeper rig / comp configuration.
#     :param fetch_project_config: set to False if you do not want to source a project configuration
#     :param fetch_logging_config: set to False if you do not want to source a logging configuration
#     :param project_name: The name of the configuration, usually project name, you want to find
#     :param send_start_log: Whether to send a log to the webserver (not desirable for libraries) [default = True]
#     :param version: Module version to add to log_record
#     :param serialization: What document format to parse
#     :return:
#     """
#     default_config = yaml.load(default_config_dict, Loader=loader.Loader)
#     default_logging = yaml.load(default_logging_dict, Loader=loader.Loader)
#     local_log_path, local_config_path = get_platform_paths(default_config, project_name)

#     # setup logging configuration
#     if fetch_logging_config:
#         if os.path.isfile(local_log_path):
#             log_config = yaml.load(open(local_log_path, "r"), Loader=loader.Loader)
#         else:
#             print("Didn't find a local logging configuration:  Using the default MPE logging.")
#             log_config = default_logging
#             cache_remote_config(log_config, local_log_path)
#         setup_logging(project_name, local_log_path, log_config, send_start_log, version)

#     # setup project configuration
#     if fetch_project_config:
#         if os.path.isfile(local_config_path):
#             project_config = yaml.load(open(local_config_path, "r"), Loader=loader.Loader)
#             project_config = deep_merge(copy.deepcopy(default_config), project_config)
#         else:
#             logging.warning(f"Could not find a local project configuration: {local_config_path}.")
#             project_config = default_config

#         return project_config


# def get_platform_paths(config, project_name):
#     """
#     Installation and other meta-data is described in the mpe defaults configuration.  This function figures out the
#     proper pathing for a given OS based on that configuration and returns it.
#     :param config: configuration dictionary containing the installation paths
#     :param project_name: The name of the configuration, usually project name, you want to find
#     :return: (local_log_path: str, local_config_path: str)
#     """
#     if "windows" in platform.platform().lower():
#         paths = config["windows_install_paths"]
#     else:
#         paths = config["linux_install_paths"]
#         paths["install"] = os.path.expanduser(paths["install"])
#     local_log_path = f'{paths["install"]}/{project_name}/{paths["local_log_config"]}/logging.yml'
#     local_config_path = f'{paths["install"]}/{project_name}/{paths["local_config"]}/{project_name}.yml'
#     return os.path.expandvars(local_log_path), os.path.expandvars(local_config_path)


def compile_remote_configuration(
    zk, project_name, config_type="configuration", rig_id=None, comp_id=None, serialization="yaml"
):
    """
    Look for various pieces of the configuration in the zookeeper tree
    :param zk: An active zookeeper connection
    :param project_name: the project name to look for
    :param config_type [hardware | projects ]
    :param rig_id: Rig ID Override
    :param comp_id: Comp ID Override
    :param serialization: The format of the document in zookeeper [yaml, ini, json, xml]
    :return: Dictionary of merged configurations
    """
    shared_config = {"shared": {}}
    rig_name = rig_id or os.environ.get("aibs_rig_id", "")
    comp_name = comp_id or os.environ.get("aibs_comp_id", "")

    mpe_defaults = fetch_configuration(zk, f"/mpe_defaults/{config_type}", required=True, serialization=serialization)

    if zk.exists(f"/projects/{project_name}"):
        project_config = fetch_configuration(
            zk, f"/projects/{project_name}/defaults/{config_type}", serialization=serialization
        )

        rig_config = fetch_configuration(
            zk, f"/rigs/{rig_name}/projects/{project_name}/{config_type}", serialization=serialization
        )

        comp_config = fetch_configuration(
            zk, f"/rigs/{comp_name}/projects/{project_name}/{config_type}", serialization=serialization
        )

        shared_rig_config = fetch_configuration(zk, f"/rigs/{rig_name}")
        shared_comp_config = fetch_configuration(zk, f"/rigs/{comp_name}")

    elif zk.exists(f"/hardware/{project_name}"):
        project_config = fetch_configuration(
            zk, f"/hardware/{project_name}/defaults/{config_type}", serialization=serialization
        )
        rig_config = fetch_configuration(
            zk, f"/rigs/{rig_name}/hardware/{project_name}/{config_type}", serialization=serialization
        )
        comp_config = fetch_configuration(
            zk, f"/rigs/{comp_name}/hardware/{project_name}/{config_type}", serialization=serialization
        )
        shared_rig_config = fetch_configuration(zk, f"/rigs/{rig_name}", serialization=serialization)
        shared_comp_config = fetch_configuration(zk, f"/rigs/{comp_name}", serialization=serialization)

    else:
        if config_type != "logging_v2":
            logging.warning(f"Found no configuration available for {project_name}")
        return mpe_defaults

    if serialization == "plain_text":  # TODO check if this works or not
        return project_config.decode()  # noqa

    rtn_dict = deep_merge(copy.deepcopy(mpe_defaults), project_config)
    rtn_dict = deep_merge(copy.deepcopy(rtn_dict), rig_config)
    rtn_dict = deep_merge(copy.deepcopy(rtn_dict), comp_config)
    if config_type != "logging_v2":
        rtn_dict = deep_merge(copy.deepcopy(rtn_dict), shared_config)
        shared_dict = deep_merge(copy.deepcopy(shared_rig_config), shared_comp_config)
        if shared_dict:
            rtn_dict["shared"] = shared_dict
    return rtn_dict


def fetch_configuration(server, config_path, required=False, serialization="yaml"):
    """
    Pull a configuration from a zk path and deserialize it.
    :param server: active zk connection
    :param config_path: path to pull data from
    :param required: whether it has to exist [default = False]
    :param serialization: the format for the document in zookeeper ['yaml', 'ini', 'json', 'xml']
    :return: YAML deserialization
    :raises: AttributeError if required and can't be deserialized
    :raises: KeyError if required but not found
    """
    config = {}
    try:
        config = server[config_path]
        if serialization == "yaml":
            config = yaml.load(server[config_path], Loader=loader.Loader)
    except (AttributeError, ParserError) as err:
        if required:
            logging.error(f"{config_path} is not valid YAML: {err}")
            exit(1)
    except KeyError:
        if required:
            logging.error(f"Could not find {config_path}.")
            exit(1)

    return config if config else {}


# def md5_equal(a, b):
#     a_s = str(a).encode()
#     b_s = str(b).encode()
#     return md5(a_s).hexdigest() == md5(b_s).hexdigest()


# def cache_remote_config(configuration, config_path):
#     """
#     Creates a directory and saves the configuration data.  if a configuration exists, it will be renamed with a
#     timestamp.
#     :param configuration: dictionary to save to dist
#     :param config_path: fully qualified path to save configuration.
#     :return:
#     """
#     config_path = os.path.expandvars(config_path)
#     os.makedirs(os.path.dirname(config_path), exist_ok=True)
#     if os.path.isfile(config_path):
#         config = yaml.load(open(config_path), Loader=loader.Loader)
#         if config == configuration:
#             return

#         timestamp = datetime.datetime.strftime(datetime.datetime.now(), "%y%m%d-%H%M%S")
#         backup_file = f"{config_path}.{timestamp}.bck"
#         logging.info(f"Copying previous configuration to {backup_file}")
#         shutil.copyfile(config_path, backup_file)

#     with open(config_path, "w") as f:
#         yaml.dump(configuration, f, default_flow_style=False)


# def dict_to_namedtuple(dictionary):
#     """
#     Utility function to change dictionaries to namedtuples recursively
#     :param dictionary: the dictionary to convert
#     :return: a namedtuple version of the dictionary contents
#     """
#     for key, value in dictionary.items():
#         if isinstance(value, dict):
#             dictionary[key] = dict_to_namedtuple(value)
#     return namedtuple("configDict", dictionary.keys())(**dictionary)


def deep_merge(dict_prime, dict_mod):
    """
    Utility function to do a deep merge on dictionaries.  Recommended to deep copy dict_prime when it's passed in as
    an argument as the original dictionary values are modified.  If a key is a list in both dicts, does not combine or
    merge these lists.  Instead, it favors the list from dict_mod.
    :param dict_prime: The dictionary to be merged into
    :param dict_mod: The dictionary to merge into the first parameter
    :return: the deep merged dictionary
    """
    for key, value in dict_mod.items():
        if isinstance(value, dict):
            if key not in dict_prime:
                dict_prime[key] = type(value)()  # For subclasses of dict
            deep_merge(dict_prime[key], dict_mod[key])
        else:
            dict_prime[key] = value
    return dict_prime
