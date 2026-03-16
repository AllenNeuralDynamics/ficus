import json
from kazoo.exceptions import NoNodeError, NotEmptyError


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
        "scratch": Node(
            name="scratch",
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
                                        "default.yml": Node(
                                            name="default.yml",
                                            value={
                                                "computer-default-value": "to rule them all",
                                            },
                                        ),
                                        "config.yml": Node(
                                            name="config.yml",
                                            value={
                                                "scope": "w11dt000001",  # overrides scope in default/software_a/config.yml
                                                "computer-layer-value": "boop boop",  # append
                                            },
                                        ),
                                    },
                                )
                            },
                        )
                    },
                ),
            },
        )
    },
)


class FakeZK:
    def __init__(self, root: dict = ZK_EXAMPLE):
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
        filename = parts[-1]
        node = self.root

        for part in parts[:-1]:
            if part not in node.children:
                node.children[part] = Node(name=part)
            node = node.children[part]

    def get(self, path):
        return self._get_zk_node(path)

    def get_children(self, path):
        return self._get_zk_node(path)[1]

    def set(self, path: str, data: dict):
        parts = path.strip("/").split("/")
        filename = parts[-1]
        node = self.root

        try:
            for part in parts[:-1]:
                if part not in node.children:
                    node.children[part] = Node(name=part)
                node = node.children[part]
            node.children[filename] = Node(name=filename, value=data)
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
