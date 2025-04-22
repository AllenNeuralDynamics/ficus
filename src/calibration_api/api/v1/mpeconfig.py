"""
A small module to specifically get MPE Configurations form our zookeeper quorum.

Copied from AIBS mpetk.mpeconfig, original author Ross Hytnen
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


default_config_dict = """
linux_install_paths:
    install: ~/.config/AIBS_MPE
    local_config: config
    local_log_config: logs
    python: /opt/mcpython3
darwin_install_paths:
    install: /var/log/aibs_mpe
    local_config: config
    local_log_config: logs
services:
    log_server: eng-logtools.corp.alleninstitute.org:9000
    python_index: http://eng-tools:3141/aibs/dev
    zookeeper: eng-logtools:2181
    issue_url: http://mpe-redirects/MPETracking
    gsid:
        host: eng-tools
        port: 6379
        db: 5 
windows_install_paths:
    install: C:/ProgramData/AIBS_MPE
    local_config: config
    local_log_config: logs
    python: C:/mcpython3
credentials:
    keepass_keyfile: C:\ProgramData\AIBS_MPE\.secrets\sipe_sw_passwords.keyx
    keepass_db: //allen/aibs/mpe/keepass/sipe_sw_passwords.kdbx
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
    config_type: Literal["configuration", "logging_v2"] = "configuration",
    version: str = None,
    rig_id: str = None,
    comp_id: str = None,
    serialization: str = "yaml",
):
    """
    Connects to the quorum and searches for the following paths:
    /mpe_defaults/[configuration | logging]
    /[projects | hardware]/<project_name>/defaults/[configuration | logging]
    /rigs/<rig_id>/[projects | hardware]/[configuration | logging]
    /rigs/<rig_id>

    :param project_name: The name of the configuration, usually project name, you want to find
    :param hosts: The quorum to connect to
    :param version: Current software version.  Can be specified but will be auto-detected if None
    :param rig_id: override for rig_id
    :param comp_id: override for comp_id
    :param serialization: the format for the document in zookeeper ['yaml', 'ini', 'json', 'xml']
    :raises: KeyError if it can't find the default configuration
    :return: dict[str, Any] of the configuration
    """

    with ConfigServer(hosts=hosts, randomize_hosts=False) as zk:
        """
        Connection to the Zookeeper Server
        """

        if not version:
            version = "unknown"

        config = compile_remote_configuration(
            zk, project_name, config_type, rig_id=rig_id, comp_id=comp_id, serialization=serialization
        )

        if config is None:
            raise ConnectionError("Error retrieving configuration from zookeeper.")

        return config


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
