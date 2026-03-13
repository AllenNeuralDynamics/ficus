import json
import yaml

from fastapi import HTTPException
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError, NotEmptyError
from loguru import logger


def get_node(zk: KazooClient, path: str) -> tuple[dict, list]:
    """Get content for a node and list of children for that node.

    :param zk: kazoo client.
    :param path: path to node.
    """
    logger.debug(f"Getting node content & children in: {path}")
    content = get_node_content(zk, path)
    children = zk.get_children(path)
    return content, children


def add_node(zk: KazooClient, path: str, data: bytes | None = None):
    """Add a node at a given path with optional data.

    :param zk: kazoo client.
    :param path: path to node.
    :param data: data to save to node.
    """
    zk.ensure_path(path)
    zk.set(path, data)


def delete_node(zk: KazooClient, path: str):
    """Delete a node at a given path.

    :param zk: kazoo client.
    :param path: path to node.
    """
    try:
        zk.delete(path)
    except NotEmptyError:
        raise NotEmptyError(f"Failed to delete node, node contains children: {path}")


################################################################################
#
#   Utilities
#
################################################################################


def get_node_content(zk: KazooClient, path: str) -> dict:
    """Get node contents at a given path, attempts to decode as YAML or JSON

    :param zk: kazoo client.
    :param path: path to node.
    """
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
