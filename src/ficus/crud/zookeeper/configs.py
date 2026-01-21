import json
import yaml

from fastapi import HTTPException
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
from loguru import logger

from ficus.schemas.configs import ConfigData


def get_all_nodes_in_path(zk: KazooClient, path: str) -> list[str]:
    """Get all nodes under a given path recursively"""
    if not zk.exists(path):
        logger.info(f"No nodes found for path: {path}")
        return []

    nodes = [path]

    try:
        children = zk.get_children(path)
        for child in children:
            child_path = f"{path}/{child}"
            nodes.extend(get_all_nodes_in_path(zk, child_path))
        return nodes
    except NoNodeError:
        logger.info(f"No node found for subpath: {path}")
        return []


def get_node(zk: KazooClient, path) -> ConfigData:
    """Get node data at a given path"""
    try:
        content = get_node_content(zk, path)
        return content
    except NoNodeError:
        logger.info(f"No node found for path: {path}")
        return {}


def add_node(zk: KazooClient, path: str, data: bytes | None = None):
    """Add a node at a given path with optional data"""
    # Create the node if it doesn't exist
    if not zk.exists(path):
        zk.create(path, b"")
        if not data:
            logger.info(f"Created node without data @ '{path}'")

    if data:
        # Set the data for the node
        zk.set(path, data)
        logger.info(f"Created node with data @ '{path}'")


################################################################################
#
#   Utilities
#
################################################################################


def get_node_content(zk: KazooClient, path: str):
    """Get node contents at a given path, attempting to decode as YAML or JSON"""
    data, _ = zk.get(path)

    if data is None:
        return None

    decoded_data = data.decode("utf-8")

    try:
        content = yaml.safe_load(decoded_data)
    except yaml.YAMLError as e:
        logger.error(f"Failed to decode file as YAML for node @ {path}: {e}")
        try:
            content = json.loads(decoded_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode file as JSON for node @ {path}: {e}")
            content = decoded_data
    return content


################################################################################
#
#   OLD CONFIGURATION FETCHING - TO BE DEPRECATED
#
################################################################################


def get_configs_old(zk: KazooClient, project_name: str, rig_name: str | None = None) -> dict | str:
    try:
        path = f"/projects/{project_name}/defaults/configuration"
        content = get_node_content(zk, path)
    except NoNodeError:
        raise HTTPException(
            status_code=404,
            detail=f"Project with name {project_name} not found",
        )

    # Deep merge with rig-specific configuration if filetype is yaml or json
    if rig_name:
        # fix later
        # parsed_rig_name = parse_rigs(rig_name)
        try:
            rig_path = f"/rigs/{rig_name}/projects/{project_name}/configuration"
            rig_content = get_node_content(zk, rig_path)
            if isinstance(rig_content, dict):
                content = deep_merge(content, rig_content)
            else:
                logger.debug(
                    f"Cannot merge rig config for {rig_name} not a valid format (yaml or json) \
                                Using rig config as is (overrides defaults)"
                )
                content = rig_content
        except NoNodeError:
            logger.debug(f"using default, rig config not found for {rig_name}")
            pass

    return content


def deep_merge(dict_prime, dict_mod):
    for key, value in dict_mod.items():
        if isinstance(value, dict):
            if key not in dict_prime:
                dict_prime[key] = type(value)()  # For subclasses of dict
            deep_merge(dict_prime[key], dict_mod[key])
        else:
            dict_prime[key] = value
    return dict_prime
