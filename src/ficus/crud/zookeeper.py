import json
import yaml

from kazoo.client import KazooClient
from kazoo.exceptions import NotEmptyError
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
        return {}

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
