import copy
import json
import yaml

from kazoo.exceptions import NoNodeError, NotEmptyError
from tests.constants import ZK_ROOT_NODE


class Node:
    def __init__(self, name: str, value: dict | None = None, children: dict | None = None):
        self.name = name
        self.value = value
        self.children = children if children else {}


"""
EXAMPLE TEST STRUCTURE
"""
ZK_EXAMPLE = Node(
    name="root",
    children={
        ZK_ROOT_NODE: Node(
            name=ZK_ROOT_NODE,
            children={
                "defaults": Node(
                    name="defaults",
                    children={
                        "software_a": Node(
                            name="software_a",
                            children={
                                "default.yml": Node(
                                    name="default.yml",
                                    value={"default-default-value": "the one ring"},
                                ),
                                "config.yml": Node(
                                    name="config.yml",
                                    value={
                                        "name": "config",
                                        "scope": "default",
                                        "default-layer-value": "beep beep",
                                    },
                                ),
                            },
                        ),
                        "software_a_default_only": Node(
                            name="software_a_default_only",
                            children={
                                "config.yml": Node(
                                    name="config.yml",
                                    value={
                                        "name": "config_defaults_only",
                                        "scope": "default",
                                        "default-layer-value": "beep beep",
                                    },
                                ),
                            },
                        ),
                    },
                ),
                "computers": Node(
                    name="computers",
                    children={
                        "w11dt000001": Node(
                            name="w11dt000001",
                            children={
                                "software_a": Node(
                                    name="software_a",
                                    children={
                                        "default.json": Node(
                                            name="default.json",
                                            value={
                                                "computer-default-value": "to rule them all",
                                            },
                                        ),
                                        "config.yml": Node(
                                            name="config.yml",
                                            value={
                                                # overrides "scope" in default/software_a/config.yml
                                                "scope": "w11dt000001",
                                                "computer-layer-value": "boop boop",  # append
                                            },
                                        ),
                                    },
                                ),
                                "software_b": Node(
                                    name="software_b",
                                    children={
                                        "default.yml": Node(
                                            name="default.yml",
                                            value={
                                                "Three Dogs Night": "one is the loneliest number",
                                            },
                                        ),
                                        "config.yml": Node(
                                            name="config.yml",
                                            value={
                                                # overrides "scope" in default/software_a/config.yml
                                                "scope": "w11dt000001",
                                                "computer-layer-value": "one one one",  # append
                                            },
                                        ),
                                    },
                                ),
                            },
                        ),
                        "w11dt000002": Node(
                            name="w11dt000002",
                            children={
                                "software_a": Node(
                                    name="software_a",
                                    children={
                                        "default.yaml": Node(
                                            name="default.yaml",
                                            value={},
                                        ),
                                        "config2.yml": Node(
                                            name="config2.yml",
                                            value={},
                                        ),
                                        "config3.json": Node(
                                            name="config3.json",
                                            value={},
                                        ),
                                    },
                                ),
                            },
                        ),
                    },
                ),
            },
        )
    },
)


class FakeZK:
    def __init__(self, root: Node = ZK_EXAMPLE):
        # Deep-copy so ZK_EXAMPLE isn't persisted between tests
        root = copy.deepcopy(ZK_EXAMPLE)
        self.root = root

    def _get_zk_node(self, path):
        parts = path.strip("/").split("/")
        node = self.root
        try:
            for part in parts:
                node = node.children[part]
            return json.dumps(node.value).encode("utf-8"), list(node.children.keys())
        except KeyError:
            raise NoNodeError

    def ensure_path(self, path):
        parts = path.strip("/").split("/")
        node = self.root

        for part in parts[:-1]:
            if part not in node.children:
                node.children[part] = Node(name=part)
            node = node.children[part]

    def exists(self, path):
        parts = path.strip("/").split("/")
        node = self.root
        try:
            for part in parts:
                node = node.children[part]
        except KeyError:
            return False
        return True

    def get(self, path):
        return self._get_zk_node(path)

    def get_children(self, path):
        return self._get_zk_node(path)[1]

    def set(self, path: str, data: bytes):
        if not isinstance(data, bytes):
            raise TypeError()
        parts = path.strip("/").split("/")
        filename = parts[-1]
        node = self.root

        if filename.endswith(".json"):
            processed_data = json.loads(data.decode("utf-8"))
        elif filename.endswith((".yml", ".yaml")):
            processed_data = yaml.safe_load(data.decode("utf-8"))
        else:
            raise ValueError(f"Unsupported file type: {filename}")

        try:
            for part in parts[:-1]:
                if part not in node.children:
                    node.children[part] = Node(name=part)
                node = node.children[part]
            node.children[filename] = Node(name=filename, value=processed_data)
        except KeyError:
            raise NoNodeError

    def delete(self, path: str):
        parts = path.strip("/").split("/")
        filename = parts[-1]
        node = self.root

        try:
            for part in parts[:-1]:
                node = node.children[part]

            if len(node.children[filename].children) > 0:
                raise NotEmptyError
            del node.children[filename]
        except KeyError:
            raise NoNodeError
